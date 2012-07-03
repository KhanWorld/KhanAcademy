
var Video = {

    SHOW_SUBTITLES_COOKIE: 'show_subtitles',

    init: function() {

        VideoControls.onYouTubeBlocked(function() {

           $("#youtube_blocked").css("visibility", "visible").css("left", "0px").css("position", "relative");
           $("#idOVideo").hide();
           VideoStats.prepareAlternativePlayer(); // If YouTube is hidden, use the flv player for statistics

        });

        var jVideoDropdown = $('#video_dropdown');
        if ( jVideoDropdown.length ) {
            jVideoDropdown.css('display', 'inline-block');

            var menu = $('#video_dropdown ol').menu();
            // Set the width explicitly before positioning it absolutely to satisfy IE7.
            menu.width(menu.width()).hide().css('position', 'absolute');
            menu.bind("menuselect", function(e, ui){
                window.location.href = ui.item.children('a').attr('href');
            });
            $(document).bind("click focusin", function(e){
                if ($(e.target).closest("#video_dropdown").length == 0) {
                    menu.hide();
                }
            });

            var button = $('#video_dropdown > a').button({
                icons: {
                    secondary: 'ui-icon-triangle-1-s'
                }
            }).show().click(function(e){
                if (menu.css('display') == 'none')
                    menu.show().menu("activate", e, $('#video_dropdown li[data-selected=selected]')).focus();
                else
                    menu.hide();
                e.preventDefault();
            });
        }

        $('.and-more').click(function(){
            $(this).hide();
            $('.more-content').show();
            return false;
        });

        $('.subtitles-link').click(function() { Video.toggleSubtitles(); return false; });
        if (readCookie(this.SHOW_SUBTITLES_COOKIE))
            this.showSubtitles();


        $('.sharepop').hide();

        $('.share-link').click(function() {
            $(this).next(".sharepop").toggle("drop",{direction:'up'},"fast");
            return false;
        });

    },

    toggleSubtitles: function() {
        if ($('.subtitles-warning').is(":visible"))
            this.hideSubtitles();
        else
            this.showSubtitles();
    },


    hideSubtitles: function() {
        eraseCookie(this.SHOW_SUBTITLES_COOKIE);
        Video.hideSubtitleElements();
    },

    hideSubtitleElements: function() {
        $('.unisubs-videoTab').hide();
        $('.subtitles-warning').hide();
        $('.youtube-video').css('marginBottom', '0px');
        Throbber.hide();
    },

    showSubtitleElements: function() {
        $('.youtube-video').css('marginBottom', '32px');
        $('.subtitles-warning').show();
        $('.unisubs-videoTab').show();
    },

    showSubtitles: function() {
        createCookie(this.SHOW_SUBTITLES_COOKIE, true, 365);
        Video.showSubtitleElements();

        if ($('.unisubs-videoTab').length == 0)
        {
            setTimeout(function() {
                Throbber.show($(".subtitles-warning"), true);
            }, 1);

            $.getScript('http://s3.www.universalsubtitles.org/js/mirosubs-widgetizer.js', function() {
                // Workaround bug where subtitles are not displayed if video was already playing until
                // video is paused and restarted.  We wait 3 secs to give subtitles a chance to load.
                setTimeout(function() {
                    if (VideoControls.player && VideoControls.player.getPlayerState() == 1 /* playing */)
                    {
                        VideoControls.pause();
                        VideoControls.play();
                    }
                }, 3000);
            });
        }
    }
}
