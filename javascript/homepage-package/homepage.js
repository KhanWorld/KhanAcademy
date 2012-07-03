var Homepage = {

    init: function() {
        VideoControls.initThumbnails();
        Homepage.initWaypoints();
        Homepage.loadData();
    },

    initPlaceholder: function(youtube_id) {

        var jelPlaceholder = $("#main-video-placeholder");

        // Once the youtube player is all loaded and ready, clicking the play
        // button will play inline.
        $(VideoControls).one("playerready", function() {

            // Before any playing, unveil and play the real youtube player
            $(VideoControls).one("beforeplay", function() {

                // Use .left to unhide the player without causing any
                // re-rendering or "pop"-in of the player.
                $(".player-loading-wrapper").css("left", 0);

            });

            jelPlaceholder.click(function(e) {

                VideoControls.play();
                e.preventDefault();

            });

        });

        // Start loading the youtube player immediately,
        // and insert it wrapped in a hidden container
        var template = Templates.get("shared.youtube-player");

        jelPlaceholder
            .parents("#main-video-link")
                .after(
                    $(template({"youtubeId": youtube_id}))
                        .wrap("<div class='player-loading-wrapper'/>")
                        .parent()
            );
    },

    initWaypoints: function() {

        // Waypoint behavior not supported in IE7-
        if ($.browser.msie && parseInt($.browser.version, 10) < 8) return;

        $.waypoints.settings.scrollThrottle = 50;

        $("#browse").waypoint(function(event, direction) {

            var jel = $(this);
            var jelFixed = $("#browse-fixed");
            var jelTop = $("#back-to-top");

            jelTop.click(function() {Homepage.waypointTop(jel, jelFixed, jelTop);});

            if (direction == "down")
                Homepage.waypointVideos(jel, jelFixed, jelTop);
            else
                Homepage.waypointTop(jel, jelFixed, jelTop);
        });
    },

    waypointTop: function(jel, jelFixed, jelTop) {
        jelFixed.css("display", "none");
        if (!$.browser.msie) jelTop.css("display", "none");
    },

    waypointVideos: function(jel, jelFixed, jelTop) {
        jelFixed.css("width", jel.width()).css("display", "block");
        if (!$.browser.msie) jelTop.css("display", "block");
        if (CSSMenus.active_menu) CSSMenus.active_menu.removeClass("css-menu-js-hover");
    },

    /**
     * Loads the contents of the playlist data.
     */
    loadData: function() {
        var cacheToken = window.Homepage_cacheToken;
        // Currently, this is being A/B tested with the conventional rendering
        // method (where everything is rendered on the server). If there is
        // no cache token, then we know we're using the old method, so don't
        // fetch the data.
        if (!cacheToken) {
            return;
        }
        $.ajax({
            type: "GET",
            url: "/api/v1/playlists/library/compact",
            dataType: "jsonp",

            // The cacheToken is supplied by the host page to indicate when the library
            // was updated. Since it's fully cacheable, the browser can pull from the
            // local client cache if it has the data already.
            data: {"v": cacheToken},

            // Explicitly specify the callback, since jQuery will otherwise put in
            // a randomly named callback and break caching.
            jsonpCallback: "__dataCb",
            success: function(data) {
                Homepage.renderLibraryContent(data);
            },
            error: function() {
                KAConsole.log("Error loading initial library data.");
            },
            cache: true
        });
    },

    renderLibraryContent: function(content) {
        var playlists = [];
        function visitTopicOrPlaylist(item) {
            if (item["playlist"]) {
                // Playlist item - add to the master list.
                playlists.push(item["playlist"]);
                return;
            }
            // Otherwise it's a topic with sub-playlists or sub-topics
            var subItems = item["items"];
            if (subItems) {
                for (var i = 0, sub; sub = subItems[i]; i++) {
                    visitTopicOrPlaylist(sub);
                }
            }
        }
        for (var i = 0, item; item = content[i]; i++) {
            visitTopicOrPlaylist(item);
        }

        // Playlists collected - go ahead and render them.
        var template = Templates.get("homepage.videolist");
        for (var i = 0, playlist; playlist = playlists[i]; i++) {
            var videos = playlist["videos"];
            var videosPerCol = Math.ceil(videos.length / 3);
            var colHeight = videosPerCol * 18;
            playlist["colHeight"] = colHeight;
            playlist["titleEncoded"] = encodeURIComponent(playlist["title"]);
            for (var j = 0, video; video = videos[j]; j++) {
                var col = (j / videosPerCol) | 0;
                video["col"] = col;
                if ((j % videosPerCol == 0) && col > 0) {
                    video["firstInCol"] = true;
                }
            }

            var sluggified = playlist["slugged_title"];
            var container = $("#" + sluggified + " ol").get(0);
            container.innerHTML = template(playlist);
        }

        content = null;
    }
};

$(function() {Homepage.init();});
