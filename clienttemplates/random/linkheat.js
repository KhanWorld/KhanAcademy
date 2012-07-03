$(function() {
    var dictViews = {},
        outliers = 6,
        rgMax = [],
        min = Number.MAX_VALUE;

    for (var ix = 0; ix < outliers; ix++)
        rgMax[rgMax.length] = Number.MIN_VALUE;

    $.ajax({
        url: "/api/v1/playlists/library/list",
        dataType: "json",
        type: "GET",
        success: function( data ) {

            $.each(data, function( ixPlaylist, playlist ) {
                $.each(playlist.videos, function( ixVideo, video ) {

                    var views = video.views;

                    rgMax[rgMax.length] = views;
                    rgMax.sort(function sortNumber( a,b ) { return a - b; });
                    rgMax = rgMax.slice(1, outliers + 1);

                    min = Math.min(min, views);

                    dictViews[video.title] = views;

                });
            });

            $("span.vid-progress").each(function() {

                var jel = $(this),
                    views = dictViews[jel.text()];

                if (views) {
                    var rgb = genRgb(views, min, rgMax[0]);

                    jel
                        .hover(
                            function() { $(this).data("htmlOld", $(this).html()).prepend("(" + views + " views) "); },
                            function() { $(this).html($(this).data("htmlOld")); })
                        .css("color", "rgb(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ")");
                }

            });

        }
    });
});

function genRgb(mag, cmin, cmax) {
    // http://code.activestate.com/recipes/52273-colormap-returns-an-rgb-tuple-on-a-0-to-255-scale-/

    var x = 0.5;

    if (cmax !== cmin)
        x = (mag - cmin) / (cmax - cmin);

    var blue = Math.min(Math.max(4 * (0.75 - x), 0.0), 1.0),
        red = Math.min(Math.max(4 * (x - 0.25), 0.0), 1.0)
        green = Math.min(Math.max(4 * Math.abs(x - 0.5) - 1.0, 0.0), 1.0)

    return [Math.floor(red * 255), Math.floor(green * 255), Math.floor(blue * 255)];
}
