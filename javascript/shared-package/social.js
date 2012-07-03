
var Social = {

    init: function(jelContainer) {
        /*--We're using a custom Twitter button, this code enables a popup--*/
        $(".twitterShare", jelContainer).click(function(event) {
            var width = 550,
                height = 370,
                left = ($(window).width() - width) / 2,
                top = ($(window).height() - height) / 2,
                url = this.href,
                opts = "status=1" +
                    ",width=" + width +
                    ",height=" + height +
                    ",top=" + top +
                    ",left=" + left;
            window.open(url, "twitter", opts);
            return false;
        });

        $(".sharepop", jelContainer).hide();

        $(".notif-share", jelContainer).click(function() {
            $(this).next(".sharepop").toggle("drop", {direction: "up"},"fast");
            return false;
        });

    },

    facebookBadge: function(desc, icon, ext, activity) {

        FB.ui({
            method: "feed",
            name: "Ik heb zojuist de " + desc + " badge verdiend" + (activity ? " met " + activity : "") + " op de Khan Academy!",
            link: "http://www.khanacademie.nl",
            picture: (icon.substring(0, 7) === "http://" ? icon : "http://www.khanacademy.org/" + icon),
            caption: "khanacademie.nl",
            description: "Jij kan dit ook behalen als je " + ext
        });
        return false;

    },
    facebookVideo: function(name, desc, url) {

        FB.ui({
            method: "feed",
            name: name,
            link: "http://www.khanacademie.nl/" + url,
            picture: "http://www.khanacademy.org/images/handtreehorizontal_facebook.png",
            caption: "khanacademie.nl",
            description: desc,
            message: "Ik heb zojuist geleerd over " + name + " op de Khan Academie"
        });
        return false;

    },

    facebookExercise: function(amount, plural, prof, exer) {

        FB.ui({
            method: "feed",
            name: amount + " vragen" + plural + " beantwoord!",
            link: "http://www.khanacademie.nl/exercisedashboard",
            picture: "http://www.khanacademy.org/images/proficient-badge-complete.png",
            caption: "khanacademie.nl",
            description: "Ik heb zojuist " + amount + " vragen" + plural + " " + prof + " " + exer + " op www.khanacademie.nl" ,
            message: "Ik heb " + exer + " geoefend op http://www.khanacademie.nl/"
        });
        return false;

    }
};

$(function() {Social.init();});
