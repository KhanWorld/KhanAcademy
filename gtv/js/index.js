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
// limitations under the License.

/**
 * @fileoverview Classes for Template Page
 *
 * 
 */

var gtv = gtv || {
  jq: {}
};


/**
 * TemplatePage class holds all the support for the page to work
 * and interact with javascript controls.
 * @constructor
 */
gtv.jq.TemplatePage = function() {
};

/**
 * Creates the main menu control.
 */
gtv.jq.TemplatePage.prototype.makeSideNav = function(selectedCategoryIndex) {
  var templatePage = this;

  var styles = {
    item: 'menu-option',
    itemDiv: 'menu-option',
    row: 'menu-row',
    chosen: 'menu-option-active',
    normal: 'menu-option-off',
    selected: 'menu-option-highlighted'
  };
  var navItems = [];

  if (!templatePage.data) {
    return;
  }

  for (var i=0; i<templatePage.data.length; i++) {
    if(templatePage.data[i].items) {
      navItems.push(templatePage.data[i].name);
    }
  }

  var behaviors = {
    orientation: 'vertical',
    selectOnInit: true
  };

  var sidenavParms = {
    createParams: {
      containerId: 'side-nav-container',
      styles: styles,
      keyController: templatePage.keyController,
      choiceCallback: function(selectedItem) {
        choiceCallback(selectedItem);
      }
    },
    behaviors: behaviors
  };

  templatePage.sideNavControl = new gtv.jq.SideNavControl(sidenavParms);

  // make sure selectedCategoryIndex is in range
  var highlightedCategoryIndex = selectedCategoryIndex;
  if (selectedCategoryIndex >= templatePage.data.length||selectedCategoryIndex < 0)
     highlightedCategoryIndex = 0;

  var showParams = {
    topParent: $('#mainMenu'),
    highlightedCategoryIndex: highlightedCategoryIndex,
    contents: {
      items: navItems
    }
  };

  templatePage.sideNavControl.showControl(showParams);

  function choiceCallback(selectedItem) {
    templatePage.makeGrid(selectedItem.data('index'));
  }


  var zone1 = new gtv.jq.KeyBehaviorZone({
    containerSelector: '#searchbox',
    navSelectors: {
      item: '.item',
      itemParent: '.item-parent',
      itemRow: '.item-row',
      itemPage: null
    },
    selectionClasses: {
      basic: 'menu-item-selected'
    },
    keyMapping: {
    },
    actions: {
    },
    useGeometry: false
  });

  templatePage.keyController.addBehaviorZone(zone1, true);

};

/**
 * Creates the grid control for the selected menu option.
 * @parm {number} selected menu option index.
 */
gtv.jq.TemplatePage.prototype.makeGrid = function( index) {
  var templatePage = this;

  var gridHolder = templatePage.gridHolder;
  if (!gridHolder) {
    gridHolder = $('#grid');
    templatePage.gridHolder = gridHolder;
  } else {
    if (templatePage.gridControl) {
      templatePage.gridControl.deleteControl();
    }
  }

  var styleClasses = {
    page: 'grid-page',
    row: 'grid-row-style',
    itemDiv: 'grid-div',
    item: '',
    description: 'grid-item-description',
    chosen: 'grid-item-active',
    normal: 'grid-item-off',
    selected: 'grid-item-highlighted'
  };

  var category = templatePage.data[index];

  if (!category.items || category.items.length == 0) {
    return;
  }

  var pageItems = [];
  var k=0;
  var pName;

  var img = $('<img></img>')
        .attr('src','http://cdn.adrise.tv/image/anime/angelic_layer_1_thumb.png')
        .addClass('slider-photo');

  for (var i=0; i<category.items.length; i++) {
    var catItem = category.items[i];


    if (catItem.playlist ) {
      var descDiv = $('<div></div>').addClass('slider-text-desc');
      pName = catItem.name;
      if( pName.length > 100 ) 
          pName = pName.substring(0,100) + '...';
      descDiv.append($('<p></p>').append(pName));
      //descDiv.append($('<p></p>').append(catItem.playlist.description));
      //pageItems.push({ content: img, description: descDiv, data:[index, k]});
      pageItems.push({ content: descDiv, data:[index, k]});
      k++;
    }
    else {
      for (var j=0; j<catItem.items.length; j++) {
        var descDiv = $('<div></div>').addClass('slider-text-desc');
        pName = catItem.name + ' : ' + catItem.items[j].name;
        if( pName.length > 100 ) 
            pName = pName.substring(0,100) + '...';
        descDiv.append($('<p></p>').append(pName));
        //pageItems.push({ content: img, description: descDiv, data:[index, k]});
        pageItems.push({ content: descDiv, data:[index, k]});
        k++;
      }
    }
  }

  var behaviors = {
    itemsPerRow: 1,
    rowsPerPage:20 
  };

  var gridParms = {
    createParams: {
      containerId: 'grid-control-container',
      styles: styleClasses,
      keyController: templatePage.keyController,
      choiceCallback: function(selectedItem) {
        choiceCallback(selectedItem);
      }
    },
    behaviors: behaviors
  };

  templatePage.gridControl = new gtv.jq.GridControl(gridParms);

  var showParams = {
    topParent: templatePage.gridHolder,
    items: pageItems
  };

  templatePage.gridControl.showControl(showParams);

  function choiceCallback(selectedItem) {
    var data = selectedItem.data('nav-data');
    location.assign('fullscreen.html?category=' + data[0] + '&item=' + data[1]);
  }
};

/**
 * Zooms the page to fit the screen.
 */
gtv.jq.TemplatePage.prototype.doPageZoom = function() {
  var templatePage = this;

  $(document.body).css('zoom', $(window).width()/1205);
};

/**
 * Starts the template page.
 */
gtv.jq.TemplatePage.prototype.start = function() {
  var templatePage = this;

  var queryString = location.search;

  var parms = queryString.substring(1).split('&');

  var selectedCategoryIndex = 0;
  var selectedItemIndex = 0;
  if (parms.length == 2) {
    selectedCategoryIndex = parseInt(parms[0].substring(9));
    selectedItemIndex = parseInt(parms[1].substring(5));
  }

  templatePage.keyController = new gtv.jq.KeyController();

  templatePage.doPageZoom();

  templatePage.dataProvider = new gtv.jq.DataProvider();
  templatePage.dataProvider.getData(function(data) {
     templatePage.data = data;
     templatePage.makeSideNav(selectedCategoryIndex);
     $(document.body).css('visibility', '');
     templatePage.keyController.start(null, true);
  });
};

new gtv.jq.TemplatePage().start();
