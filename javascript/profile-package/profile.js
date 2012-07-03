/**
 * Code to handle the logic for the profile page.
 */
// TODO: clean up all event listeners. This page does not remove any
// event listeners when tearing down the graphs.

var Profile = {
    version: 0,
    initialGraphUrl: null, // Filled in by the template after script load.
    email: null,  // Filled in by the template after script load.
    fLoadingGraph: false,
    fLoadedGraph: false,
    userGoalsHref: '',

    init: function() {

        $('.share-link').hide();
        $('.sharepop').hide();

        $(".achievement,.exercise,.video").hover(
            function () {
                $(this).find(".share-link").show();
                },
            function () {
                $(this).find(".share-link").hide();
                $(this).find(".sharepop").hide();
              });

        $('.share-link').click(function() {
            if ( $.browser.msie && (parseInt($.browser.version, 10) < 8) ) {
                $(this).next(".sharepop").toggle();
            } else {
                $(this).next(".sharepop").toggle(
                        "drop", { direction:'up' }, "fast" );
            }
            return false;
        });

        // Init Highcharts global options.
        Highcharts.setOptions({
            credits: {
                enabled: false
            },
            title: {
                text: ''
            },
            subtitle: {
                text: ''
            }
        });


        if ($.address){

            // this is hackish, but it prevents the change event from being fired twice on load
            if ( $.address.value() === "/" ){
                window.location = window.location + "#" + $(".graph-link:eq(0)").attr("href");
            }

            $.address.change(function( evt ){

                if ( $.address.path() !== "/"){
                    Profile.historyChange( evt );
                }

            });

        }

        $(".graph-link").click(
            function(evt){
                evt.preventDefault();
                if($.address){
                    // only visit the resource described by the url, leave the params unchanged
                    var href = $( this ).attr( "href" )
                    var path = href.split("?")[0];

                    // visiting a different resource
                    if ( path !== $.address.path() ){
                        $.address.path( path );
                    }

                    // applying filters for same resource via querystring
                    else{
                        // make a dict of current qs params and merge with the link's
                        var currentParams = {};
                        _.map( $.address.parameterNames(), function(e){ currentParams[e] = $.address.parameter( e ); } );
                        var linkParams = Profile.parseQueryString( href );
                        $.extend( currentParams, linkParams );

                        $.address.queryString( Profile.reconstructQueryString( currentParams ) );
                    }
                }
            }
        );

        $("#individual_report #achievements #achievement-list > ul li").click(function() {
             var category = $(this).attr('id');
             var clickedBadge = $(this);

             $("#badge-container").css("display", "");
             clickedBadge.siblings().removeClass("selected");

             if ($("#badge-container > #" + category ).is(":visible")) {
                if (clickedBadge.parents().hasClass("standard-view")) {
                    $("#badge-container > #" + category ).slideUp(300, function(){
                            $("#badge-container").css("display", "none");
                            clickedBadge.removeClass("selected");
                        });
                }
                else {
                    $("#badge-container > #" + category ).hide();
                    $("#badge-container").css("display", "none");
                    clickedBadge.removeClass("selected");
                }
             }
             else {
                var jelContainer = $("#badge-container");
                var oldHeight = jelContainer.height();
                $(jelContainer).children().hide();
                if (clickedBadge.parents().hasClass("standard-view")) {
                    $(jelContainer).css("min-height", oldHeight);
                    $("#" + category, jelContainer).slideDown(300, function() {
                        $(jelContainer).animate({"min-height": 0}, 200);
                    });
                } else {
                    $("#" + category, jelContainer).show();
                }
                clickedBadge.addClass("selected");
             }
        });

        // remove goals from IE<=8
        $(".lte8 .goals-accordion-content").remove();

        $("#stats-nav #nav-accordion")
            .accordion({
                header:".header",
                active:".graph-link-selected",
                autoHeight: false,
                clearStyle: true
            });

        setTimeout(function(){
            if (!Profile.fLoadingGraph && !Profile.fLoadedGraph)
            {
                // If 1000 millis after document.ready fires we still haven't
                // started loading a graph, load manually.
                // The externalChange trigger may have fired before we hooked
                // up a listener.
                Profile.historyChange();
            }
        }, 1000);

        Profile.ProgressSummaryView = new ProgressSummaryView();
    },
    highlightPoints: function(chart, fxnHighlight) {

        if (!chart) return;

        for (var ix = 0; ix < chart.series.length; ix++) {
            var series = chart.series[ix];

            this.muteSeriesStyles(series);

            for (var ixData = 0; ixData < series.data.length; ixData++) {
                var pointOptions = series.data[ixData].options;
                if (!pointOptions.marker) pointOptions.marker = {};
                pointOptions.marker.enabled = fxnHighlight(pointOptions);
                if (pointOptions.marker.enabled) pointOptions.marker.radius = 6;
            }

            series.isDirty = true;
        }

        chart.redraw();
    },

    muteSeriesStyles: function(series) {
        if (series.options.fMuted) return;

        series.graph.attr('opacity', 0.1);
        series.graph.attr('stroke', '#CCCCCC');
        series.options.lineWidth = 1;
        series.options.shadow = false;
        series.options.fMuted = true;
    },

    accentuateSeriesStyles: function(series) {
        series.options.lineWidth = 3.5;
        series.options.shadow = true;
        series.options.fMuted = false;
    },

    highlightSeries: function(chart, seriesHighlight) {

        if (!chart || !seriesHighlight) return;

        for (var ix = 0; ix < chart.series.length; ix++)
        {
            var series = chart.series[ix];
            var fSelected = (series == seriesHighlight);

            if (series.fSelectedLast == null || series.fSelectedLast != fSelected)
            {
                if (fSelected)
                    this.accentuateSeriesStyles(series);
                else
                    this.muteSeriesStyles(series);

                for (var ixData = 0; ixData < series.data.length; ixData++) {
                    series.data[ixData].options.marker = {
                        enabled: fSelected,
                        radius: fSelected ? 5 : 4
                    };
                }

                series.isDirty = true;
                series.fSelectedLast = fSelected;
            }
        }

        var options = seriesHighlight.options;
        options.color = '#0080C9';
        seriesHighlight.remove(false);
        chart.addSeries(options, false, false);

        chart.redraw();
    },

    collapseAccordion: function() {
        // Turn on collapsing, collapse everything, and turn off collapsing
        $("#stats-nav #nav-accordion").accordion(
                "option", "collapsible", true).accordion(
                    "activate", false).accordion(
                        "option", "collapsible", false);
    },

    baseGraphHref: function(href) {
        // regex for matching scheme:// part of uri
        // see http://tools.ietf.org/html/rfc3986#section-3.1
        var reScheme = /^\w[\w\d+-.]*:\/\//;
        var match = href.match(reScheme);
        if (match) {
            href = href.substring(match[0].length);
        }

        var ixSlash = href.indexOf("/");
        if (ixSlash > -1)
            href = href.substring(href.indexOf("/"));

        var ixQuestionMark = href.indexOf("?");
        if (ixQuestionMark > -1)
            href = href.substring(0, ixQuestionMark);

        return href;
    },

    /**
     * Expands the navigation accordion according to the link specified.
     * @return {boolean} whether or not a link was found to be a valid link.
     */
    expandAccordionForHref: function(href) {
        if (!href) {
            return false;
        }

        href = this.baseGraphHref(href);

        href = href.replace(/[<>']/g, "");
        var selectorAccordionSection =
                ".graph-link-header[href*='" + href + "']";
        if ( $(selectorAccordionSection).length ) {
            $("#stats-nav #nav-accordion").accordion(
                    "activate", selectorAccordionSection);
            return true;
        }

        this.collapseAccordion();
        return false;
    },

    styleSublinkFromHref: function(href) {

        if (!href) return;

        var reDtStart = /dt_start=[^&]+/;

        var matchStart = href.match(reDtStart);
        var sDtStart = matchStart ? matchStart[0] : "dt_start=lastweek";

        href = href.replace(/[<>']/g, "");

        $(".graph-sub-link").removeClass("graph-sub-link-selected");
        $(".graph-sub-link[href*='" + this.baseGraphHref(href) + "'][href*='" + sDtStart + "']").addClass("graph-sub-link-selected");
    },

    // called whenever user clicks graph type accordion
    loadGraphFromLink: function(el) {
        if (!el) return;
        Profile.loadGraphStudentListAware(el.href);
    },

    loadGraphStudentListAware: function(url) {
        var $dropdown = $('#studentlists_dropdown ol');
        if ($dropdown.length == 1) {
            var list_id = $dropdown.data('selected').key;
            var qs = this.parseQueryString(url);
            qs['list_id'] = list_id;
            qs['version'] = Profile.version;
            qs['dt'] = $("#targetDatepicker").val();
            url = this.baseGraphHref(url) + '?' + this.reconstructQueryString(qs);
        }

        this.loadGraph(url);
    },

    loadFilters : function( href ){
        // fix the hrefs for each filter
        var a = $("#stats-filters a[href^=\"" + href + "\"]").parent();
        $("#stats-filters .filter:visible").not(a).slideUp("slow");
        a.slideDown();
    },

    loadGraph: function(href, fNoHistoryEntry) {
        var apiCallbacksTable = {
            '/api/v1/user/goals': this.renderUserGoals,
            '/api/v1/user/exercises': this.renderExercisesTable,
            '/api/v1/user/students/goals': this.renderStudentGoals,
            '/api/v1/user/students/progressreport': window.ClassProfile ? ClassProfile.renderStudentProgressReport : null,
            '/api/v1/user/students/progress/summary': this.ProgressSummaryView.render
        };

        if (!href) return;

        if (this.fLoadingGraph) {
            setTimeout(function(){Profile.loadGraph(href);}, 200);
            return;
        }

        this.styleSublinkFromHref(href);
        this.fLoadingGraph = true;
        this.fLoadedGraph = true;

        var apiCallback = null;
        for (var uri in apiCallbacksTable) {
            if (href.indexOf(uri) > -1) {
                apiCallback = apiCallbacksTable[uri];
            }
        }

        $.ajax({
            type: "GET",
            url: Timezone.append_tz_offset_query_param(href),
            data: {},
            dataType: apiCallback ? 'json' : 'html',
            success: function(data){
                Profile.finishLoadGraph(data, href, fNoHistoryEntry, apiCallback);
            },
            error: function() {
                Profile.finishLoadGraphError();
            }
        });
        $("#graph-content").html("");
        this.showGraphThrobber(true);
    },

    finishLoadGraph: function(data, href, fNoHistoryEntry, apiCallback) {

        this.fLoadingGraph = false;

        if (!fNoHistoryEntry) {
            // Add history entry for browser
            //             if ($.address) {
            //                 $.address(href);
            // }
        }

        this.showGraphThrobber(false);
        this.styleSublinkFromHref(href);

        var start = (new Date).getTime();
        if (apiCallback) {
            apiCallback(data, href);
        } else {
            $("#graph-content").html(data);
        }
        var diff = (new Date).getTime() - start;
        KAConsole.log('API call rendered in ' + diff + ' ms.');
    },

    renderUserGoals: function(data, href) {
        current_goals = [];
        completed_goals = [];
        abandoned_goals = [];

        var qs = Profile.parseQueryString(href);
        // We don't handle the difference between API calls requiring email and
        // legacy calls requiring student_email very well, so this page gets
        // called with both. Need to fix the root cause (and hopefully redo all
        // the URLs for this page), but for now just be liberal in what we
        // accept.
        var qsEmail = qs.email || qs.student_email || null;
        var viewingOwnGoals = qsEmail === null || qsEmail === USER_EMAIL;

        $.each(data, function(idx, goal) {
            if (goal.completed) {
                if (goal.abandoned)
                    abandoned_goals.push(goal);
                else
                    completed_goals.push(goal);
            } else {
                current_goals.push(goal);
            }
        });
        if (viewingOwnGoals)
            GoalBook.reset(current_goals);
        else
            CurrentGoalBook = new GoalCollection(current_goals);
        CompletedGoalBook = new GoalCollection(completed_goals);
        AbandonedGoalBook = new GoalCollection(abandoned_goals);

        $("#graph-content").html('<div id="current-goals-list"></div><div id="completed-goals-list"></div><div id="abandoned-goals-list"></div>');

        Profile.goalsViews = {};
        Profile.goalsViews.current = new GoalProfileView({
            el: "#current-goals-list",
            model: viewingOwnGoals ? GoalBook : CurrentGoalBook,
            type: 'current',
            readonly: !viewingOwnGoals
        });
        Profile.goalsViews.completed = new GoalProfileView({
            el: "#completed-goals-list",
            model: CompletedGoalBook,
            type: 'completed',
            readonly: true
        });
        Profile.goalsViews.abandoned = new GoalProfileView({
            el: "#abandoned-goals-list",
            model: AbandonedGoalBook,
            type: 'abandoned',
            readonly: true
        });

        Profile.userGoalsHref = href;
        Profile.showGoalType('current');

        if (completed_goals.length > 0) {
            $('#goal-show-completed-link').parent().show();
        } else {
            $('#goal-show-completed-link').parent().hide();
        }
        if (abandoned_goals.length > 0) {
            $('#goal-show-abandoned-link').parent().show();
        } else {
            $('#goal-show-abandoned-link').parent().hide();
        }

        if (viewingOwnGoals) {
            $('.new-goal').addClass('green').removeClass('disabled').click(function(e) {
                e.preventDefault();
                window.newGoalDialog.show();
            });
        }
    },

    showGoalType: function(type) {
        if (Profile.goalsViews) {
            $.each(['current','completed','abandoned'], function(idx, atype) {
                if (type == atype) {
                    Profile.goalsViews[atype].show();
                    $('#goal-show-' + atype + '-link').addClass('graph-sub-link-selected');
                } else {
                    Profile.goalsViews[atype].hide();
                    $('#goal-show-' + atype + '-link').removeClass('graph-sub-link-selected');
                }
            });
        }
    },

    renderStudentGoals: function(data, href) {
        var studentGoalsViewModel = {
            rowData: [],
            sortDesc: '',
            filterDesc: ''
        };

        $.each(data, function(idx1, student) {
            student.goal_count = 0;
            student.most_recent_update = null;
            student.profile_url = "/profile?student_email="+ student.email +"#/api/v1/user/goals?email="+student.email;

            if (student.goals != undefined && student.goals.length > 0) {
                $.each(student.goals, function(idx2, goal) {
                    // Sort objectives by status
                    var progress_count = 0;
                    var found_struggling = false;

                    goal.objectiveWidth = 100/goal.objectives.length;
                    goal.objectives.sort(function(a,b) { return b.progress-a.progress; });

                    $.each(goal.objectives, function(idx3, objective) {
                        Goal.calcObjectiveDependents(objective, goal.objectiveWidth);

                        if (objective.status == 'proficient')
                            progress_count += 1000;
                        else if (objective.status == 'started' || objective.status == 'struggling')
                            progress_count += 1;

                        if (objective.status == 'struggling') {
                            found_struggling = true;
                            objective.struggling = true;
                        }
                        objective.statusCSS = objective.status ? objective.status : "not-started";

                        objective.objectiveID = idx3;
                    });

                    if (!student.most_recent_update || goal.updated > student.most_recent_update)
                        student.most_recent_update = goal;

                    student.goal_count++;
                    row = {
                        rowID: studentGoalsViewModel.rowData.length,
                        student: student,
                        goal: goal,
                        progress_count: progress_count,
                        goal_idx: student.goal_count,
                        struggling: found_struggling
                    };

                    $.each(goal.objectives, function(idx3, objective) {
                        objective.row = row;
                    });
                    studentGoalsViewModel.rowData.push(row);
                });
            } else {
                studentGoalsViewModel.rowData.push({
                    rowID: studentGoalsViewModel.rowData.length,
                    student: student,
                    goal: {objectives: []},
                    progress_count: -1,
                    goal_idx: 0,
                    struggling: false
                });
            }
        });

        var template = Templates.get( "profile.profile-class-goals" );
        $("#graph-content").html( template(studentGoalsViewModel) );

        $("#class-student-goal .goal-row").each(function() {
            var jRowEl = $(this);
            var goalViewModel = studentGoalsViewModel.rowData[jRowEl.attr('data-id')];
            goalViewModel.rowElement = this;
            goalViewModel.countElement = jRowEl.find('.goal-count');
            goalViewModel.startTimeElement = jRowEl.find('.goal-start-time');
            goalViewModel.updateTimeElement = jRowEl.find('.goal-update-time');

            Profile.AddObjectiveHover(jRowEl);

            jRowEl.find("a.objective").each(function() {
                var obj = goalViewModel.goal.objectives[$(this).attr('data-id')];
                obj.blockElement = this;

                if ( obj.internal_id !== "" &&
                    (obj.type === "GoalObjectiveExerciseProficiency" ||
                     obj.type === "GoalObjectiveAnyExerciseProficiency")
                ) {
                    $(this).click(function( e ) {
                        e.preventDefault();
                        Profile.collapseAccordion();
                        var url = Profile.exerciseProgressUrl(obj.internal_id,
                            goalViewModel.student.email);
                        Profile.loadGraph(url);
                    });
                }
            });
        });

        $("#student-goals-sort").change(function() { Profile.sortStudentGoals(studentGoalsViewModel); });

        $("input.student-goals-filter-check").change(function() { Profile.filterStudentGoals(studentGoalsViewModel); });
        $("#student-goals-search").keyup(function() { Profile.filterStudentGoals(studentGoalsViewModel); });

        Profile.sortStudentGoals(studentGoalsViewModel);
        Profile.filterStudentGoals(studentGoalsViewModel);
    },
    sortStudentGoals: function(studentGoalsViewModel) {
        var sort = $("#student-goals-sort").val();
        var show_updated = false;

        if (sort == 'name') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (b.student.nickname > a.student.nickname)
                    return -1;
                if (b.student.nickname < a.student.nickname)
                    return 1;
                return a.goal_idx-b.goal_idx;
            });

            studentGoalsViewModel.sortDesc = 'student name';
            show_updated = false; // started

        } else if (sort == 'progress') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                return b.progress_count - a.progress_count;
            });

            studentGoalsViewModel.sortDesc = 'goal progress';
            show_updated = true; // updated

        } else if (sort == 'created') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (a.goal && !b.goal)
                    return -1;
                if (b.goal && !a.goal)
                    return 1;
                if (a.goal && b.goal) {
                    if (b.goal.created > a.goal.created)
                        return 1;
                    if (b.goal.created < a.goal.created)
                        return -1;
                }
                return 0;
            });

            studentGoalsViewModel.sortDesc = 'goal creation time';
            show_updated = false; // started

        } else if (sort == 'updated') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (a.goal && !b.goal)
                    return -1;
                if (b.goal && !a.goal)
                    return 1;
                if (a.goal && b.goal) {
                    if (b.goal.updated > a.goal.updated)
                        return 1;
                    if (b.goal.updated < a.goal.updated)
                        return -1;
                }
                return 0;
            });

            studentGoalsViewModel.sortDesc = 'last work logged time';
            show_updated = true; // updated
        }

        var container = $('#class-student-goal').detach();
        $.each(studentGoalsViewModel.rowData, function(idx, row) {
            $(row.rowElement).detach();
            $(row.rowElement).appendTo(container);
            if (show_updated) {
                row.startTimeElement.hide();
                row.updateTimeElement.show();
            } else {
                row.startTimeElement.show();
                row.updateTimeElement.hide();
            }
        });
        container.insertAfter('#class-goal-filter-desc');

        Profile.updateStudentGoalsFilterText(studentGoalsViewModel);
    },
    updateStudentGoalsFilterText: function(studentGoalsViewModel) {
        var text = 'Sorted by ' + studentGoalsViewModel.sortDesc + '. ' + studentGoalsViewModel.filterDesc + '.';
        $('#class-goal-filter-desc').html(text);
    },
    filterStudentGoals: function(studentGoalsViewModel) {
        var filter_text = $.trim($("#student-goals-search").val().toLowerCase());
        var filters = {};
        $("input.student-goals-filter-check").each(function(idx, element) {
            filters[$(element).attr('name')] = $(element).is(":checked");
        });

        studentGoalsViewModel.filterDesc = '';
        if (filters['most-recent']) {
            studentGoalsViewModel.filterDesc += 'most recently worked on goals';
        }
        if (filters['in-progress']) {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'goals in progress';
        }
        if (filters['struggling']) {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'students who are struggling';
        }
        if (filter_text != '') {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'students/goals matching "' + filter_text + '"';
        }
        if (studentGoalsViewModel.filterDesc != '')
            studentGoalsViewModel.filterDesc = 'Showing only ' + studentGoalsViewModel.filterDesc;
        else
            studentGoalsViewModel.filterDesc = 'No filters applied';

        var container = $('#class-student-goal').detach();

        $.each(studentGoalsViewModel.rowData, function(idx, row) {
            var row_visible = true;

            if (filters['most-recent']) {
                row_visible = row_visible && (!row.goal || (row.goal == row.student.most_recent_update));
            }
            if (filters['in-progress']) {
                row_visible = row_visible && (row.goal && (row.progress_count > 0));
            }
            if (filters['struggling']) {
                row_visible = row_visible && (row.struggling);
            }
            if (row_visible) {
                if (filter_text == '' || row.student.nickname.toLowerCase().indexOf(filter_text) >= 0) {
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            $(objective.blockElement).removeClass('matches-filter');
                        });
                    }
                } else {
                    row_visible = false;
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            if ((objective.description.toLowerCase().indexOf(filter_text) >= 0)) {
                                row_visible = true;
                                $(objective.blockElement).addClass('matches-filter');
                            } else {
                                $(objective.blockElement).removeClass('matches-filter');
                            }
                        });
                    }
                }
            }

            if (row_visible)
                $(row.rowElement).show();
            else
                $(row.rowElement).hide();

            if (filters['most-recent'])
                row.countElement.hide();
            else
                row.countElement.show();
        });

        container.insertAfter('#class-goal-filter-desc');

        Profile.updateStudentGoalsFilterText(studentGoalsViewModel);
    },

    finishLoadGraphError: function() {
        this.fLoadingGraph = false;
        this.showGraphThrobber(false);
        $("#graph-content").html("<div class='graph-notification'>It's our fault. We ran into a problem loading this graph. Try again later, and if this continues to happen please <a href='/reportissue?type=Defect'>let us know</a>.</div>");
    },

    /**
     * Renders the exercise blocks given the JSON blob about the exercises.
     */
    renderExercisesTable: function(data) {
        var templateContext = [];

        for ( var i = 0, exercise; exercise = data[i]; i++ ) {
            var stat = "Not started";
            var color = "";
            var states = exercise["exercise_states"];
            var totalDone = exercise["total_done"];

            if ( states["reviewing"] ) {
                stat = "Review";
                color = "review light";
            } else if ( states["proficient"] ) {
                // TODO: handle implicit proficiency - is that data in the API?
                // (due to proficiency in a more advanced module)
                stat = "Proficient";
                color = "proficient";
            } else if ( states["struggling"] ) {
                stat = "Struggling";
                color = "struggling";
            } else if ( totalDone > 0 ) {
                stat = "Started";
                color = "started";
            }

            if ( color ) {
                color = color + " action-gradient seethrough";
            } else {
                color = "transparent";
            }
            var model = exercise["exercise_model"];
            templateContext.push({
                "name": model["name"],
                "color": color,
                "status": stat,
                "shortName": model["short_display_name"] || model["display_name"],
                "displayName": model["display_name"],
                "progress": Math.floor( exercise["progress"] * 100 ) + "%",
                "totalDone": totalDone
            });
        }
        var template = Templates.get( "profile.exercise_progress" );
        $("#graph-content").html( template({ "exercises": templateContext }) );

        Profile.hoverContent($("#module-progress .student-module-status"));
        $("#module-progress .student-module-status").click(function(e) {
            $("#info-hover-container").hide();
            Profile.collapseAccordion();
            // Extract the name from the ID, which has been prefixed.
            var exerciseName = this.id.substring( "exercise-".length );
            var url = Profile.exerciseProgressUrl(exerciseName, Profile.email);
            Profile.loadGraph(url);
        });
    },

    // TODO: move history management out to a common utility
    historyChange: function(e) {
        var href = ( $.address.value() === "/" ) ? this.initialGraphUrl : $.address.value();
        var url = ( $.address.path() === "/" ) ? this.initialGraphUrl : $.address.path();
        if ( href ) {
            if ( this.expandAccordionForHref(href) ) {
                this.loadGraph( href , true );
                this.loadFilters( url );
            } else {
                // Invalid URL - just try the first link available.
                var links = $(".graph-link");
                if ( links.length ) {
                    Profile.loadGraphFromLink( links[0] );
                }
            }
        }
    },

    showGraphThrobber: function(fVisible) {
        if (fVisible)
            $("#graph-progress-bar").progressbar({value: 100}).slideDown("fast");
        else
            $("#graph-progress-bar").slideUp("fast");
    },

    // TODO: move this out to a more generic utility file.
    parseQueryString: function(url) {
        var qs = {};
        var parts = url.split('?');
        if(parts.length == 2) {
            var querystring = parts[1].split('&');
            for(var i = 0; i<querystring.length; i++) {
                var kv = querystring[i].split('=');
                if(kv[0].length > 0) { //fix trailing &
                    key = decodeURIComponent(kv[0]);
                    value = decodeURIComponent(kv[1]);
                    qs[key] = value;
                }
            }
        }
        return qs;
    },

    // TODO: move this out to a more generic utility file.
    reconstructQueryString: function(hash, kvjoin, eljoin) {
        kvjoin = kvjoin || '=';
        eljoin = eljoin || '&';
        qs = [];
        for(var key in hash) {
            if(hash.hasOwnProperty(key))
                qs.push(key + kvjoin + hash[key]);
        }
        return qs.join(eljoin);
    },

    exerciseProgressUrl: function(exercise, email) {
        return "/profile/graph/exerciseproblems" +
            "?exercise_name=" + exercise +
            "&student_email=" + encodeURIComponent(email);
    },

    hoverContent: function(elements) {
        var lastHoverTime;
        var mouseX;
        var mouseY;

        elements.hover(
            function( e ) {
                var hoverTime = +(new Date());
                lastHoverTime = hoverTime;
                mouseX = e.pageX;
                mouseY = e.pageY;
                var el = this;
                setTimeout(function() {
                    if (hoverTime != lastHoverTime) {
                        return;
                    }

                    var hoverData = $(el).children(".hover-data");
                    var html = $.trim(hoverData.html());
                    if ( html ) {
                        var jelGraph = $("#graph-content");
                        var leftMax = jelGraph.offset().left +
                                jelGraph.width() - 150;
                        var left = Math.min(mouseX + 15, leftMax);

                        var jHoverEl = $("#info-hover-container");
                        if ( jHoverEl.length === 0 ) {
                            jHoverEl = $('<div id="info-hover-container"></div>').appendTo('body');
                        }
                        jHoverEl
                            .html(html)
                            .css({left: left, top: mouseY + 5})
                            .show();
                    }
                }, 100);
            },
            function( e ) {
                lastHoverTime = null;
                $("#info-hover-container").hide();
            }
        );
    },

    AddObjectiveHover: function(element) {
        Profile.hoverContent(element.find(".objective"));
    }
};

var GoalProfileView = Backbone.View.extend({
    template: Templates.get( "profile.profile-goals" ),
    needsRerender: true,

    initialize: function() {
        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
        this.model.bind('remove', this.render, this);
        this.model.bind('add', this.render, this);

        // only hookup event handlers if the view allows edits
        if (this.options.readonly) return;

        $(this.el)
            // edit titles
            .delegate('input.goal-title', 'focusout', $.proxy(this.changeTitle, this))
            .delegate('input.goal-title', 'keypress', $.proxy(function( e ) {
                if (e.which == '13') { // enter
                    e.preventDefault();
                    this.changeTitle(e);
                    $(e.target).blur();
                }
            }, this))
            .delegate('input.goal-title', 'keyup', $.proxy(function( e ) {
                if ( e.which == '27' ) { // escape
                    e.preventDefault();

                    // restore old title
                    var jel = $(e.target);
                    var goal = this.model.get(jel.closest('.goal').data('id'));
                    jel.val(goal.get('title'));

                    jel.blur();
                }
            }, this))

            // show abandon button on hover
            .delegate('.goal', 'mouseenter mouseleave', function( e ) {
                var el = $(e.currentTarget);
                if ( e.type == 'mouseenter' ) {
                    el.find(".goal-description .summary-light").hide();
                    el.find(".goal-description .goal-controls").show();
                } else {
                    el.find(".goal-description .goal-controls").hide();
                    el.find(".goal-description .summary-light").show();
                }
            })
            // respond to abandon button
            .delegate('.abandon', 'click', $.proxy(this.abandon, this));
    },

    changeTitle: function( e, options ) {
        var jel = $(e.target);
        var goal = this.model.get(jel.closest('.goal').data('id'));
        var newTitle = jel.val();
        if (newTitle !== goal.get('title')) {
            goal.save({title: newTitle});
        }
    },

    show: function() {
        // render if necessary
        if (this.needsRerender) {
            this.render();
        }
        $(this.el).show();
    },

    hide: function() {
        $(this.el).hide();
    },

    render: function() {
        var jel = $(this.el);
        // delay rendering until the view is actually visible
        this.needsRerender = false;
        var json = _.pluck(this.model.models, 'attributes');
        jel.html(this.template({
            goals: json,
            isCurrent: (this.options.type == 'current'),
            isCompleted: (this.options.type == 'completed'),
            isAbandoned: (this.options.type == 'abandoned'),
            readonly: this.options.readonly
        }));

        // attach a NewGoalView to the new goals html
        var newGoalEl = this.$(".goalpicker");
        if ( newGoalEl.length > 0) {
            this.newGoalsView = new NewGoalView({
                el: newGoalEl,
                model: this.model
            });
        }

        Profile.AddObjectiveHover(jel);
        return jel;
    },

    abandon: function( evt ) {
        var goalEl = $(evt.target).closest('.goal');
        var goal = this.model.get(goalEl.data('id'));
        if ( !goal ) {
            // haven't yet received a reponse from the server after creating the
            // goal. Shouldn't happen too often, so just show a message.
            alert("Please wait a few seconds and try again. If this is the second time you've seen this message, reload the page");
            return;
        }

        if (confirm("Abandoning a goal is permanent and cannot be undone. Do you really want to abandon this goal?")) {
            // move the model to the abandoned collection
            this.model.remove(goal);
            goal.set({'abandoned': true});
            AbandonedGoalBook.add(goal);

            // persist to server
            goal.save().fail(function() {
                KAConsole.log("Warning: failed to abandon goal", goal);
                AbandonedGoalBook.remove(goal);
                this.model.add(goal);
            });
        }
    }
});

var ProgressSummaryView = function() {
    var fInitialized = false,
        template = Templates.get("profile.class-progress-summary"),
        statusInfo = {
                'not-started': {
                    fShowOnLeft: true,
                    order: 0},
                struggling: {
                    fShowOnLeft: true,
                    order: 1},
                started: {
                    fShowOnLeft: false,
                    order: 2},
                proficient: {
                    fShowOnLeft: false,
                    order:  3},
                review: {
                    fShowOnLeft: false,
                    order: 4}
            },
        updateFilterTimeout = null;

    function toPixelWidth(num) {
        return Math.round(200 * num / Profile.numStudents);
    }

    function filterSummaryRows() {
        updateFilterTimeout = null;
        var filterText = $("#student-progresssummary-search").val()
                            .trim().toLowerCase();

        $(".exercise-row").each(function(index) {
            var jel = $(this),
                exerciseName = jel.find(".exercise-name span")
                                .text().toLowerCase();
            if (filterText === "" || exerciseName.indexOf(filterText) > -1) {
                jel.show();
            } else {
                jel.hide();
            }
        });
    }

    function init() {
        fInitialized = true;

        // Register partials and helpers
        Handlebars.registerPartial("class-progress-column", Templates.get("profile.class-progress-column"));

        Handlebars.registerHelper("toPixelWidth", function(num) {
            return toPixelWidth(num);
        });

        Handlebars.registerHelper("toNumberOfStudents", function(num) {
            if (toPixelWidth(num) < 20) {
                return "";
            }
            return num;
        });

        Handlebars.registerHelper("toDisplay", function(status) {
            if (status === "not-started") {
                return "unstarted";
            }
            return status;
        });

        Handlebars.registerHelper("progressColumn", function(block) {
            this.progressSide = block.hash.side;
            return block(this)
        });

        Handlebars.registerHelper("progressIter", function(progress, block) {
            var result = "",
                fOnLeft = (block.hash.side === "left");

            $.each(progress, function(index, p) {
                if (fOnLeft === statusInfo[p.status].fShowOnLeft) {
                    result += block(p);
                }
            });

            return result;
        });

        // Delegate clicks to expand rows and load student graphs
        $("#graph-content").delegate(".exercise-row", "click", function(e) {
            var jRow = $(this),
                studentLists = jRow.find(".student-lists");

            if (studentLists.is(":visible")) {
                jRow.find(".segment").each(function(index) {
                    var jel = $(this),
                        width = jel.data("width"),
                        span = width < 20 ? "" : jel.data("num");
                    jel.animate({width: width}, 350, "easeInOutCubic")
                        .find("span").html(span);
                });

                studentLists.fadeOut(100, "easeInOutCubic");
            } else {
                jRow.find(".segment").animate({width: 100}, 450, "easeInOutCubic", function() {
                    var jel = $(this),
                        status = jel.data("status");
                    jel.find("span").html(status);
                });

                studentLists.delay(150).fadeIn(650, "easeInOutCubic");
            }
        });

        $("#graph-content").delegate(".student-link", "click", function(e) {
            e.preventDefault();

            var jel = $(this),
                exercise = jel.data("exercise"),
                email = jel.data("email");

            Profile.collapseAccordion();
            var url = Profile.exerciseProgressUrl(exercise, email);
            Profile.loadGraph(url);
        });

        $("#stats-filters").delegate("#student-progresssummary-search", "keyup", function() {
            if (updateFilterTimeout == null) {
                updateFilterTimeout = setTimeout(filterSummaryRows, 250);
            }
        });

    }

    return {
        render: function(context) {
            if (!fInitialized) {
                init();
            }

            Profile.numStudents = context.num_students;

            $.each(context.exercises, function(index, exercise) {
                exercise.progress.sort(function(first, second) {
                    return statusInfo[first.status].order - statusInfo[second.status].order;
                });
            });

            $("#graph-content").html(template(context));
        }
    };
};

$(function(){Profile.init();});
