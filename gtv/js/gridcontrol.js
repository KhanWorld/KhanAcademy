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
 * @fileoverview Classes for Grid Control
 *
 * 
 */

var gtv = gtv || {
  jq: {}
};

/**
 * GridControlParams class holds configuration values specific to GridControl.
 * @constructor
 */
gtv.jq.GridControlParams = function() {
};

/**
 * CreateParams for the GridControl control.
 * @type {CreateParams}
 */
gtv.jq.GridControlParams.prototype.createParams = null;

/**
 * Behaviors for the GridControl control.
 * @type {GridControlBehaviors}
 */
gtv.jq.GridControlParams.prototype.behaviors = null;

/**
 * GridControlBehaviors configures the behaviors for a GridControl control.
 * @constructor
 */
gtv.jq.GridControlBehaviors = function() {
};

/**
 * Tells the GridControl control the number of items per row.
 * @type {number}
 */
gtv.jq.GridControlBehaviors.prototype.itemsPerRow = null;

/**
 * Tells the GridControl control the number of rows per page.
 * @type {number}
 */
gtv.jq.GridControlBehaviors.prototype.rowsPerPage = null;

/**
 * GridControl class. GridControl control is a vertical scrolling control
 * that can manage selection or contain other controls within a grid layout.
 * @param {gtv.jq.GridControlParams} gridControlParams
 * @constructor
 */
gtv.jq.GridControl = function(gridControlParams)
{
  this.params_ = jQuery.extend(gridControlParams.createParams, gridControlParams);
}

/**
 * Removes the control from its container and from the key controller.
 */
gtv.jq.GridControl.prototype.deleteControl = function()
{
  if (!this.container)
    return;

  this.keyController.removeBehaviorZone(this.behaviorZone);
  this.container.remove();
  this.container = null;
};

/**
 * Creates a new GridControl with the specified items and adds it to a
 * container on the page.
 * @param {gtv.jq.ShowParams} controlParams Params for creating the control.
 * @return {boolean} true on success
 */
gtv.jq.GridControl.prototype.showControl = function(controlParams)
{
  this.params_ = jQuery.extend(this.params_, controlParams);

  if (!this.params_.containerId)
    return false;

  var pageItems = this.params_.items;

  if (!pageItems || pageItems.length == 0)
    return false;

  var gridControl = this;

  gridControl.topParent = this.params_.topParent;
  gridControl.styles = this.params_.styles || {};
  gridControl.keyController = this.params_.keyController;
  gridControl.behaviors = this.params_.behaviors || {};

  gridControl.choiceCallback = this.params_.choiceCallback;

  gridControl.containerId = this.params_.containerId;

  var container = $('<div></div>')
    .attr('id', gridControl.containerId)
    .addClass('grid-control');

  gridControl.topParent.append(container);

  gridControl.container = container;

  var windowWidth = container.width();
  var containerOffset = container.offset();
  var parentOffset = gridControl.topParent.position();
  var windowHeight = $(window).height() - containerOffset.top;

  var itemCount = pageItems.length;
  var rowCount = 0;
  var itemRow;
  // start at 1, will be calculated after first item
  var itemsPerRow = gridControl.behaviors.itemsPerRow || 1;
  // start at 1, will be calculated after first item
  var rowsPerPage = gridControl.behaviors.rowsPerPage || 1;

  var firstPage;
  var page;
  var pageCount = 0;

  function addItem(i)
  {
    if (i % itemsPerRow == 0) {
      if (rowCount % rowsPerPage == 0) {
        page = $('<div></div>').addClass('grid-item-page ' +
                                         gridControl.styles.page);

  	page.data('page', pageCount);

        container.append(page);
        pageCount++;
      }

      itemRow = $('<div></div>').addClass('grid-item-row ' +
                                          gridControl.styles.row);
      page.append(itemRow);
      itemRow.data('row', rowCount % rowsPerPage);

      rowCount++;
    }
    var content = pageItems[i].content;
    var description = pageItems[i].description;
    var navData = pageItems[i].data;

    var itemTextHolder = $('<div></div>')
      .addClass('grid-item-text-holder ' + gridControl.styles.description);

    if (description)
      itemTextHolder.append(description);

    var item = $('<div></div>')
      .addClass('grid-item ' + gridControl.styles.normal)
      .data("index", i % itemsPerRow)
      .append(content);

    if (navData)
      item.data("nav-data", navData);

    var itemDiv = $('<div></div>')
      .addClass('grid-item-div ' + gridControl.styles.itemDiv)
      .append(item)
      .append(itemTextHolder);

    itemRow.append(itemDiv);

    return itemRow;
  }


  for (var index = 0; index < itemCount; index++) {
    var newItemRow = addItem(index);

    if (index == 0) {
      var newItemDiv = newItemRow.find('.grid-item-div');
      var newItemDivWidth = newItemDiv.outerWidth();

      var newItemRowHeight = newItemRow.outerHeight();

      if (!gridControl.behaviors.itemsPerRow) {
      	itemsPerRow = Math.max(1, Math.floor(windowWidth / newItemDivWidth));
      }

      if (!gridControl.behaviors.rowsPerPage) {
      	rowsPerPage = Math.max(1, Math.floor(windowHeight / newItemRowHeight));
      }
    }
  }


  var keyMapping = {
    13: function(selectedItem, newItem) {  // enter
      if (gridControl.choiceCallback) {
        gridControl.choiceCallback(selectedItem);
      }
      return { status: 'none' };
    }
  };

  var navSelectors = {
    item: '.grid-item',
    itemParent: '.grid-item-div',
    itemRow: '.grid-item-row',
    itemPage: '.grid-item-page'
  };

  var selectionClasses = {
    basic: gridControl.styles.selected
  };

  var lastSelected;
  var actions = {
    scrollIntoView: function(selectedItem, newItem, getFinishCallback) {
      gridControl.showPage(selectedItem, newItem, getFinishCallback);
    },
    click: function(selectedItem, newItem) {
      if (gridControl.choiceCallback) {
        gridControl.choiceCallback(selectedItem);
      }
    }
  };

  var zoneParms = {
    containerSelector: '#' + gridControl.containerId,
    keyMapping: keyMapping,
    actions: actions,
    navSelectors: navSelectors,
    selectionClasses: selectionClasses,
    navigableData: 'nav-data'
  };

  gridControl.behaviorZone = new gtv.jq.KeyBehaviorZone(zoneParms);

  gridControl.keyController.addBehaviorZone(gridControl.behaviorZone, true);

  return true;
};

/**
 * Selects a GridControl item, scrolling if necesary.
 * @param {jQuery.Element} current selected item.
 * @param {jQuery.Element} new selected item.
 * @param {SynchronizedCallback.acquireCallback} callback to be called once the GridControl
 * 		scrolling ends.
 */
gtv.jq.GridControl.prototype.showPage = function(selectedItem,
                                             newItem,
                                             getFinishCallback)
{
  if (!newItem) {
    return;
  }

  if (!selectedItem)
    selectedItem = this.container.find('.grid-item').first();

  var divPos = this.topParent.position();
  var divDim = {
    width: this.topParent.width(),
    height: this.topParent.height()
  };
  var liPos = newItem.parent().position();
  var liDim = {
    width:newItem.parent().width(),
    height:newItem.parent().height()
  };

  if ((liPos.top - divPos.top + liDim.height + 100) >
      divDim.height) {
    this.topParent.animate({
        scrollTop:this.topParent.scrollTop() + liDim.height
      },
      getFinishCallback());
  }
  else if (liPos.top - divPos.top - this.topParent.scrollTop() < 0) {
    this.topParent.animate({
        scrollTop:this.topParent.scrollTop() - liDim.height
      },
      getFinishCallback());
  }

};
