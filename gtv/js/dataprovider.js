// Copyright 2010 Google Inc. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and

/**
 * @fileoverview Classes for DataProvider
 *
 * 
 */

var gtv = gtv || {
  jq: {}
};

/**
 * DataProvider class. Defines a provider for all data (Categories, Images & Videos) shown in the template.
 */
gtv.jq.DataProvider = function() {
};

/**
 * Returns all data shown in the template..
 * @return {object} with the following structure:
 *    - categories -> [category1, category2, ..., categoryN].
 *    - category -> {name, items}.
 *    - items -> [item1, item2, ..., itemN]
 *    - item -> {image, title, description, videos}
 *    - videos -> {thumb, title, subtitle, description, sources}
 *    - sources -> [source1, source2, ..., sourceN]
 *    - source -> string with the url | {src, type, codecs}
 */
gtv.jq.DataProvider.prototype.getData = function(processVideos) {


/*
  function getRandom(max) {
    return Math.floor(Math.random() * max);
  }

  function getThumbId(small) {
    var max = small?15:14;
    var num = getRandom(max);
    if (num == 0) {
      num = 1;
    }
    if (num < 10) {
      num = '0' + num;
    }
    return num.toString();
  }

  var categories = [
    'Dev Events',
    'Technology',
    'Conferences',
    'Keynotes',
    'Talks',
    'Events'];

  var playLists = [
    'I/O Keynotes',
    'Google Developer Day',
    'Google Chrome',
    'Apps Marketplace'];

  var sources = [
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
        + 'IO2010-Keynote-day1.mp4',
      title: '2010 Day 1 Keynote',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'IO2010-Keynote-day2-android.mp4',
      title: '2010 Day 2 Keynote',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
        + 'IO2009-Keynote-day1.mp4',
      title: '2009 Day 1 Keynote',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
        + 'GDD2010-Highlights.mp4',
      title: '2010 Highlights',
      desc: 'Google Developer Day'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'GDD2010-BR-Keynote.mp4',
      title: '2010 Keynote',
      desc: 'Brazil'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'ChromeFrame.mp4',
      title: 'Using Google Chrome Frame',
      desc: 'Alex Russell'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CWS-HowTo.mp4',
      title: 'Uploading your App',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CWS-GettingStarted.mp4',
      title: 'Getting Started with Apps for the Chrome Web Store',
      desc: 'Arne Roomann-Kurrik'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'Chrome-Accessibility.mp4',
      title: 'Google Chrome Extensions and Accessibility',
      desc: 'Rachel Shearer'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CF1-AppsMarketplace-Part1.mp4',
      title: 'Campfire Part 1',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CF1-AppsMarketplace-Part2.mp4',
      title: 'Campfire Part 1',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CF1-AppsMarketplace-Part3.mp4',
      title: 'Campfire Part 1',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CF1-AppsMarketplace-Part4.mp4',
      title: 'Campfire Part 1',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CF1-AppsMarketplace-Part5.mp4',
      title: 'Campfire Part 1',
      desc: 'Moscone Center'
    },
    {
      src:'http://commondatastorage.googleapis.com/gtv_template_assets/'
          + 'CF1-AppsMarketplace-Part6.mp4',
      title: 'Campfire Part 1',
      desc: 'Moscone Center'
    }
  ];

  var data = {
    categories: []
  };

  for (var i=0; i<categories.length; i++) {
    var category = {
      name: categories[i],
      items: []
    };

    for (var j=0; j<9; j++) {
      var subcategory = {
        image: 'images/thumbs/thumb' + getThumbId() + '.jpg',
        title: playLists[getRandom(playLists.length)],
        description: ['Google Dev Events'],
        videos: []
      };

      for (var k=0; k<25; k++) {
        var videoInfo = sources[getRandom(sources.length)];
        var video = {
          thumb: 'images/thumbs/thumb' + getThumbId(true) + '-s.jpg',
          title: videoInfo.title,
          subtitle: videoInfo.desc,
          description: [],
          sources: [videoInfo.src]
        };
        subcategory.videos.push(video);
      }

      category.items.push(subcategory);
    }

    data.categories.push(category);

*/


    $.getJSON('http://www.khanacademy.org/api/v1/playlists/library', function(data) {
//    $.getJSON('/topics_list', function(data) {
      processVideos(data);
    });

//  }

//  return data;
};

