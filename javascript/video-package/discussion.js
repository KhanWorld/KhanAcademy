
var Discussion = {

    init: function() {
        VideoControls.initJumpLinks();
    },

    updateRemaining: function(max, textSelector, charsSelector, charCountSelector, parent) {
        setTimeout(function(){
            var c = 0;
            try {
                c = max - parseInt($(textSelector, parent).val().length);
            }
            catch(e) {
                return;
            };

            if (c <= 0)
                $(charsSelector, parent).addClass("chars_remaining_none");
            else
                $(charsSelector, parent).removeClass("chars_remaining_none");

            // Disable submit buttons within form so user can't submit and lose clipped content.
            var jForm = $(textSelector, parent).parents("form");
            if (jForm.length)
            {
                if (c < 0)
                    $("input[type=button]", jForm).addClass("buttonDisabled").attr("disabled", "disabled");
                else
                    $("input[type=button]", jForm).removeClass("buttonDisabled").removeAttr("disabled");
            }

            $(charCountSelector, parent).html(c);
        }, 1);
    }
};

var Voting = {

    init: function() {
        $(".vote_for").live("click", Voting.voteEntity);
    },

    voteEntity: function(e) {

        if (QA.showNeedsLoginNote(this, "to vote.")) return false;

        var jel = $(this);

        var vote_type = parseInt(jel.attr("data-vote_type"));
        if (!vote_type) return;

        var key = jel.attr("data-key");
        if (!key) return false;

        var fAbstain = jel.is(".voted");

        var jelParent = jel.parents(".comment, .answer, .question").first();
        var jelVotes = jelParent.find(".sum_votes");
        var votes = parseInt($.trim(jelVotes.attr("data-sum_original")));

        $.post("/discussion/voteentity", {
            entity_key: key,
            vote_type: fAbstain ? 0 : vote_type
            },
            function(data) { Voting.finishVoteEntity(data, jel, jelParent, jelVotes, votes); }
        );

        Voting.clearVote(jel, jelParent, jelVotes, votes);

        var votesNext = votes + (fAbstain ? 0 : vote_type);

        if (jelParent.is(".comment"))
            jelVotes.html(votesNext + " vote" + (votesNext == 1 ? "" : "s") + ", ");
        else
            jelVotes.html(votesNext);

        jelVotes.addClass("sum_votes_changed");
        if (!fAbstain) jel.addClass("voted");

        return false;
    },

    clearVote: function(jel, jelParent, jelVotes, votes) {
        jelParent.find("a.vote_for").removeClass("voted");
        jelVotes.removeClass("sum_votes_changed").html(votes);
    },

    finishVoteEntity: function(data, jel, jelParent, jelVotes, votes) {
        try { eval("var dict_json = " + data); }
        catch(e) { return; }

        if (dict_json && dict_json.error)
        {
            this.clearVote(jel, jelParent, jelVotes, votes);
            QA.showInfoNote(jel.get(0), dict_json.error);
        }
    }

};

var Moderation = {

    init: function() {
        $(".mod_show").live("click", Moderation.showTools);
        $(".mod_tools .mod_edit").live("click", Moderation.editEntity);
        $(".mod_tools .mod_delete").live("click", Moderation.deleteEntity);
        $(".mod_tools .mod_change").live("click", Moderation.changeEntityType);

        $(".flag_show").live("click", Moderation.showFlagTools);
        $(".flag_tools .flag_as").live("click", Moderation.flagEntity);
    },

    showTools: function() {

        var parent = $(this).parents(".mod_tools");
        if (!parent.length) return;

        $(".mod_tools_show", parent).css("display", "none");
        $(".mod_tools_hidden", parent).css("display", "");

        return false;
    },

    showFlagTools: function() {

        if (QA.showNeedsLoginNote(this, "to flag this item.")) return false;

        var parent = $(this).parents(".flag_tools");
        if (!parent.length) return false;

        $(".flag_tools_show", parent).css("display", "none");
        $(".flag_tools_hidden", parent).css("display", "");

        return false;
    },

    flagEntity: function() {

        var flag = $(this).attr("data-flag");
        if (!flag) return;

        return Moderation.actionWithoutConfirmation(this,
                "/discussion/flagentity",
                {flag: flag},
                "flagged!");
    },

    deleteEntity: function() {
        return Moderation.actionWithConfirmation(this,
                "/discussion/deleteentity",
                null,
                "Are you sure you want to delete this?",
                "deleted!");
    },

    editEntity: function() {
        QA.edit(this);
        return false;
    },

    changeEntityType: function() {
        var target_type = $(this).attr("data-target_type");
        if (!target_type) return;

        return Moderation.actionWithConfirmation(this,
                "/discussion/changeentitytype",
                {target_type: target_type},
                "Are you sure you want to change this to a " + target_type + "?",
                "changed to " + target_type + "!");
    },

    actionWithConfirmation: function(el, sUrl, data, sConfirm, sCompleted) {

        if (!confirm(sConfirm)) return false;

        this.actionWithoutConfirmation(el, sUrl, data, sCompleted);

        return false;
    },

    actionWithoutConfirmation: function(el, sUrl, data, sCompleted) {

        var key = $(el).attr("data-key");
        if (!key) return false;

        if (!data) data = {};
        data["entity_key"] = key;

        $.post(sUrl, data);
        Moderation.finishedAction(el, sCompleted);

        return false;
    },

    finishedAction: function(el, sMsg) {
        var parent = $(el).parents(".tools_hidden");
        if (!parent.length) return;

        parent.text(sMsg);
        Throbber.hide();
    }

};

var QA = {

    page: 0,

    init: function() {

        var jQuestionText = $(".question_text");
        jQuestionText.focus(QA.focusQuestion);
        jQuestionText.change(QA.updateRemainingQuestion).keyup(QA.updateRemainingQuestion);
        jQuestionText.placeholder();

        $("form.questions").submit(function(){return false;});

        $("input.question_submit, input.answer_submit").live("click", QA.submit);
        $(".question_cancel, .answer_cancel").live("click", QA.cancel);
        $(".questions_container .question_container")
            .live("mouseover", QA.hover)
            .live("mouseout", QA.unhover)
            .live("click", QA.expand);
        $(".close_note").live("click", QA.closeNote);

        $(window).resize(QA.repositionStickyNote);

        QA.loadPage($("#qa_page").val() || 0, true, $("#qa_expand_key").val());
        QA.enable();
    },

    initPagesAndQuestions: function() {
        $("form.answers").submit(function(){return false;});
        $("a.questions_page").click(function(){ QA.loadPage($(this).attr("page")); return false; });
        $(".add_yours").click(QA.expandAndFocus);
        $(".answer_text").focus(QA.focusAnswer).placeholder();
    },

   submit: function() {

        var parent = QA.getQAParent(this);
        if (!parent.length) return;

        var type = $(parent).is(".answer_container") ? "answer" : "question";

        var jText = $("." + type + "_text", parent);

        if (!$.trim(jText.val()).length) return;
        if (jText.val() == jText.attr("placeholder")) return;

        var data_suffix = "&page=" + QA.page;

        var sUrl = "/discussion/add" + type;
        var jData = $("form." + type, parent);

        var fxnCallback = type == "question" ? QA.finishSubmitQuestion : QA.finishSubmitAnswer;

        if (QA.isInsideExistingQA(this))
        {
            sUrl = "/discussion/editentity";
            jData = $("textarea:first, input[name=entity_key]:first", parent);
            var jPlaylist = $("#playlist_key:first");
            jData = jData.add(jPlaylist);
        }

        $.post(sUrl,
                jData.serialize() + data_suffix,
                function(data) {fxnCallback(data, jText[0]);});

        QA.disable();
        Throbber.show($("." + type + "_cancel", parent));
    },

    finishSubmitQuestion: function(data, el) {
        setTimeout(function(){QA.cancel.apply(el)}, 1);
        QA.finishLoadPage(data);
        QA.enable();
    },

    finishSubmitAnswer: function(data, el) {

        var parent = QA.getQuestionParent(el);
        if (!parent.length) return;

        try { eval("var dict_json = " + data); }
        catch(e) { return; }

        setTimeout(function(){QA.cancel.apply(el)}, 1);
        $(".answers_container", parent).html(dict_json.html);
        VideoControls.initJumpLinks();
        Throbber.hide();
        QA.enable();
    },

    loadPage: function(page, fInitialLoad, qa_expand_key) {

        try { page = parseInt(page); }
        catch(e) { return; }

        if (page < 0) return;

        $.get("/discussion/pagequestions",
                {
                    video_key: $("#video_key").val(),
                    playlist_key: $("#playlist_key").val(),
                    sort: $("#sort").val(),
                    qa_expand_key: qa_expand_key,
                    page: page
                },
                function(data) { QA.finishLoadPage(data, fInitialLoad); });

        if (!fInitialLoad) Throbber.show($(".questions_page_controls span"));
    },

    finishLoadPage: function(data, fInitialLoad) {
        try { eval("var dict_json = " + data); }
        catch(e) { return; }

        $(".questions_container").html(dict_json.html);
        QA.page = dict_json.page;
        QA.initPagesAndQuestions();
        if (!fInitialLoad) Throbber.hide();
        VideoControls.initJumpLinks();

        var hash = "qa";
        if (dict_json.qa_expand_key)
            hash = "q_" + dict_json.qa_expand_key;

        if (!fInitialLoad || hash != "qa")
            document.location = "#" + hash;
    },

    getQAParent: function(el) {
        var parentAnswer = $(el).parents("div.answer_container");
        if (parentAnswer.length) return parentAnswer;
        return QA.getQuestionParent(el);
    },

    getQuestionParent: function(el) {
        return $(el).parents("div.question_container");
    },

    isInsideExistingQA: function(el) {
        var parent = QA.getQAParent(el);
        if (!parent.length) return false;
        return $(".sig", parent).length > 0;
    },

    updateRemainingQuestion: function() {
        Discussion.updateRemaining(500, ".question_text",
                                        ".question_add_controls .chars_remaining",
                                        ".question_add_controls .chars_remaining_count");
    },

    disable: function() {
        $(".question_text, .answer_text").attr("disabled", "disabled");
        $(".question_submit, .answer_submit").addClass("buttonDisabled").attr("disabled", "disabled");
    },

    enable: function() {
        $(".question_text, .answer_text").removeAttr("disabled");
        $(".question_submit, .answer_submit").removeClass("buttonDisabled").removeAttr("disabled");
    },

    showNeedsLoginNote: function(el, sMsg) {
        return this.showNote($(".login_note"), el, sMsg, function(){$(".login_link").focus();});
    },

    showInfoNote: function(el, sMsg) {
        return this.showNote($(".info_note"), el, sMsg);
    },

    closeNote: function() {
        $(".note").hide();
        return false;
    },

    showNote: function(jNote, el, sMsg, fxnCallback) {
        if (jNote.length && el)
        {
            $(".note_desc", jNote).text(sMsg);

            var jTarget = $(el);
            var offset = jTarget.offset();
            var offsetContainer = $("#video-page").offset();

            jNote.css("visibility", "hidden").css("display", "");
            var top = offset.top - offsetContainer.top + (jTarget.height() / 2) - (jNote.height() / 2);
            var left = offset.left - offsetContainer.left + (jTarget.width() / 2) - (jNote.width() / 2);
            jNote.css("top", top).css("left", left).css("visibility", "visible").css("display", "");

            if (fxnCallback) setTimeout(fxnCallback, 50);

            return true;
        }
        return false;
    },

    edit: function(el) {
        var parent = QA.getQAParent(el);

        if (!parent.length) return;

        var type = $(parent).is(".answer_container") ? "answer" : "question";

        var jEntity = $("." + type, parent);
        var jControls = $("." + type + "_controls_container", parent);
        var jSignature = $("." + type + "_sig", parent);

        if (!jEntity.length || !jControls.length || !jSignature.length) return;

        jEntity.addClass(type + "_placeholder").removeClass(type);
        jSignature.css("display", "none");
        jControls.slideDown();

        // Build up a textarea with plaintext content
        var jTextarea = $("<textarea name='" + type + "_text' class='" + type + "_text' rows=2 cols=40></textarea>");

        // Replace BRs with newlines.  Must use {newline} placeholder instead of \n b/c IE
        // doesn't preserve newline content when asking for .text() content below.
        var reBR = /<br>/gi;
        var reBRReverse = /{newline}/g;
        var jSpan = $("span", jEntity).first();
        var htmlEntity = $.browser.msie ? jSpan.html().replace(reBR, "{newline}") : jSpan.html();

        var jContent = $("<div>").html(htmlEntity);

        // Remove any artificially inserted ellipsis
        $(".ellipsisExpand", jContent).remove();

        // Fill, insert, then focus textarea
        var textEntity = $.browser.msie ? jContent.text().replace(reBRReverse, "\n") : jContent.text();
        jTextarea.val($.trim(textEntity));
        jSpan.css("display", "none").after(jTextarea);

        setTimeout(function(){jTextarea.focus();}, 1);
    },

    focusQuestion: function() {

        if (QA.showNeedsLoginNote(this, "to ask your question.")) return false;

        var parent = QA.getQAParent(this);
        if (!parent.length) return;

        $(".question_controls_container", parent).slideDown("fast");
        QA.updateRemainingQuestion();
        QA.showStickyNote();
    },

    cancel: function() {
        var parent = QA.getQAParent(this);
        if (!parent.length) return;

        var type = $(parent).is(".answer_container") ? "answer" : "question";

        $("." + type + "_text", parent).val("").placeholder();

        if (type == "question") QA.hideStickyNote();

        $("." + type + "_controls_container", parent).slideUp("fast");

        if (QA.isInsideExistingQA(this))
        {
            $("textarea", parent).first().remove();
            $("span", parent).first().css("display", "");
            $("." + type + "_placeholder", parent).addClass(type).removeClass(type + "_placeholder");
            $("." + type + "_sig", parent).slideDown("fast");
        }

        return false;
    },

    focusAnswer: function() {

        if (QA.showNeedsLoginNote(this, "to answer this question.")) return false;

        var parent = QA.getQAParent(this);
        if (!parent.length) return;

        $(".answer_controls_container", parent).slideDown("fast");
    },

    hover: function() {
        if ($(this).is(".question_container_expanded")) return;

        $(this).addClass("question_container_hover");
    },

    unhover: function() {
        if ($(this).is(".question_container_expanded")) return;

        $(this).removeClass("question_container_hover");
    },

    repositionStickyNote: function() {
        if ($(".sticky_note").is(":visible")) QA.showStickyNote();
    },

    showStickyNote: function() {
        $(".sticky_note").slideDown("fast");
    },

    hideStickyNote: function() {
        $(".sticky_note").slideUp("fast");
    },

    expandAndFocus: function(e) {

        var parent = QA.getQAParent(this);
        if (!parent.length) return;

        QA.expand.apply(parent[0], [e, function(){$(".answer_text", parent).focus();}]);
        return false;
    },

    expand: function(e, fxnCallback) {
        if ($(this).is(".question_container_expanded")) return;

        var jContentUrlized = $(".question span.question_content_urlized", this);
        $(".question a.question_link", this).replaceWith(jContentUrlized);
        jContentUrlized.css("display", "");
        $(".question_answer_count", this).css("display", "none");
        $(".answers_and_form_container", this).slideDown("fast", fxnCallback);

        QA.unhover.apply(this);

        $(this).addClass("question_container_expanded");

        var key = $(".question", this).attr("data-question_key");
        $.post("/discussion/expandquestion",
                {qa_expand_key: key},
                function(){ /* Fire and forget */ });

        // If user clicks on a link inside of a question during the expand, don't follow the link.
        // YouTube API "5:42"-style links will still control the player in this circumstance.
        if (e) e.preventDefault();
    }

};

var Comments = {

    page: 0,

    init: function() {
        $("a.comment_add").click(Comments.add);
        $("a.comment_show").click(Comments.show);
        $("a.comment_cancel").click(Comments.cancel);
        $("input.comment_submit").click(Comments.submit);
        $("form.comments").submit(function(){return false;});
        $(".comment_text").change(Comments.updateRemaining).keyup(Comments.updateRemaining);

        Comments.loadPage(0, true);
        Comments.enable();
    },

    initPages: function() {
        $("a.comments_page").click(function(){ Comments.loadPage($(this).attr("page")); return false; });
        $("span.ellipsisExpand").click(Comments.expand);
    },

    expand: function() {
        var parent = $(this).parents("div.comment");
        if (!parent.length) return;

        $(this).css("display", "none");
        $("span.hiddenExpand", parent).removeClass("hiddenExpand");
    },

    loadPage: function(page, fInitialLoad) {

        try { page = parseInt(page); }
        catch(e) { return; }

        if (page < 0) return;

        $.get("/discussion/pagecomments",
                {
                    video_key: $("#video_key").val(),
                    playlist_key: $("#playlist_key").val(),
                    page: page
                },
                function(data) { Comments.finishLoadPage(data, fInitialLoad); });

        if (!fInitialLoad) Throbber.show($(".comments_page_controls span"));
    },

    finishLoadPage: function(data, fInitialLoad) {
        try { eval("var dict_json = " + data); }
        catch(e) { return; }

        $(".comments_container").html(dict_json.html);
        Comments.page = dict_json.page;
        Comments.initPages();
        if (!fInitialLoad) Throbber.hide();
        VideoControls.initJumpLinks();

        if (!fInitialLoad)
            document.location = "#comments";
    },

    add: function() {
        $(this).css("display", "none");
        $("div.comment_form").slideDown("fast", function(){$(".comment_text").focus();});
        Comments.updateRemaining();
        return false;
    },

    cancel: function() {
        $("a.comment_add").css("display", "");
        $("div.comment_form").slideUp("fast");
        $(".comment_text").val("");
        return false;
    },

    show: function() {
        $("div.comments_hidden").slideDown("fast");
        $(".comments_show_more").css("display", "none");
        return false;
    },

    submit: function() {

        if (!$.trim($(".comment_text").val()).length) return;

        var fCommentsHidden = $("div.comments_hidden").length && !$("div.comments_hidden").is(":visible");
        var data_suffix = "&comments_hidden=" + (fCommentsHidden ? "1" : "0");
        $.post("/discussion/addcomment",
                $("form.comments").serialize() + data_suffix,
                Comments.finishSubmit);

        Comments.disable();
        Throbber.show($(".comment_cancel"));
    },

    finishSubmit: function(data) {
        Comments.finishLoadPage(data);
        $(".comment_text").val("");
        Comments.updateRemaining();
        Comments.enable();
        Comments.cancel();
    },

    disable: function() {
        $(".comment_text, .comment_submit").attr("disabled", "disabled");
        $(".comment_submit").addClass("buttonDisabled");
    },

    enable: function() {
        $(".comment_text, .comment_submit").removeAttr("disabled");
        $(".comment_submit").removeClass("buttonDisabled");
    },

    updateRemaining: function() {
        Discussion.updateRemaining(300, ".comment_text",
                                        ".comment_add_controls .chars_remaining",
                                        ".comment_add_controls .chars_remaining_count");
    }

};

// Now that we enable YouTube's JS api so we can control the player w/ "{minute}:{second}"-style links,
// we are vulnerable to a bug in IE's flash player's removeCallback implementation.  This wouldn't harm
// most users b/c it only manifests itself during page unload, but for anybody with IE's "show all errors"
// enabled, it becomes an annoying source of "Javascript error occurred" popups on unload.
// So we manually fix up the removeCallback function to be a little more forgiving.
// See http://www.fusioncharts.com/forum/Topic12189-6-1.aspx#bm12281, http://swfupload.org/forum/generaldiscussion/809,
// and http://www.longtailvideo.com/support/forums/jw-player/bug-reports/10374/javascript-error-with-embed.
$(window).unload(
function() {
    (function($){
        $(function(){
            if (typeof __flash__removeCallback != 'undefined'){
                __flash__removeCallback = function(instance, name){
                    if (instance != null && name != null)
                        instance[name] = null;
                };
            }
        });
    })(jQuery);
});
