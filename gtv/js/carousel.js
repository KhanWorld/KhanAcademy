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
 * @fileoverview Classes for Carousel Control
 *
 * 
 */

var gtv = gtv || {
  jq: {}
};

/**
 * CarouselParams class holds configuration values specific to Carousel.
 * @constructor
 */
gtv.jq.CarouselParams = function() {
};

/**
 * CreateParams for the Carousel control.
 * @type {CreateParams}
 */
gtv.jq.CarouselParams.prototype.createParams = null;

/**
 * Behaviors for the Carousel control.
 * @type {CarouselBehaviors}
 */
gtv.jq.CarouselParams.prototype.behaviors = null;

/**
 * CarouselBehaviors configures the behaviors for a Carousel control.
 * @constructor
 */
gtv.jq.CarouselBehaviors = function() {
};

/**
 * Tells the Carousel control if an item should be selected on init.
 * @type {boolean}
 */
gtv.jq.CarouselBehaviors.prototype.selectOnInit = null;

/**
 * Tells the Carousel control the number of items that will be displayed (visible).
 * @type {number}
 */
gtv.jq.CarouselBehaviors.prototype.itemsToDisplay = null;

/**
 * Tells the Carousel control if it should do auto-scrolling.
 * @type {boolean}
 */
gtv.jq.CarouselBehaviors.prototype.autoScroll = null;

/**
 * Tells the Carousel control the auto-scrolling interval in milliseconds.
 * Valid only if autoScroll behavior is true.
 * @type {number}
 */
gtv.jq.CarouselBehaviors.prototype.autoScrollInterval = null;

/**
 * Carousel class. Carousel control is a horizontal scrolling control
 * that can manage selection or contain other controls.
 * @param {gtv.jq.CarouselParams} carouselParams
 * @constructor
 */
gtv.jq.Carousel = function(carouselParams) {
  this.params_ = jQuery.extend(carouselParams.createParams, carouselParams);
};

/**
 * Removes the control from its container and from the key controller.
 */
gtv.jq.Carousel.prototype.deleteControl = function() {
  if (!this.container) {
    return;
  }

  this.keyController.removeBehaviorZone(this.behaviorZone);

  this.container.remove();
  this.container = null;
};

/**
 * Creates a new Carousel with the specified items and adds it to a
 * container on the page.
 * @param {gtv.jq.ShowParams} controlParams Params for creating the control.
 * @return {boolean} true on success
 */
gtv.jq.Carousel.prototype.showControl = function(controlParams) {
  this.params_ = jQuery.extend(this.params_, controlParams);

  this.topParent = this.params_.topParent;
  this.containerId = this.params_.containerId;
  this.parentSelector = '#' + this.topParent.attr('id');
  this.styles = this.params_.styles || {};
  this.items = this.params_.items;
  this.behaviors = this.params_.behaviors || {};
  this.keyController = this.params_.keyController;
  this.callbacks = this.params_.callbacks || {};
  this.layers = this.params_.layerNames || ['default'];

  var items = this.items;

  this.deleteControl();

  var container = $('<div></div>')
      .attr('id', this.containerId)
      .addClass('carousel-control');
  if (this.styles.container) {
    container.addClass(this.styles.container);
  }

  this.topParent.append(container);
  this.container = container;

  for (var i=0; i<items.length; i++) {
    var content = items[i].content;
    var description = items[i].description;
    var navData = items[i].data;
    var addCallback = items[i].addCallback;

    var itemTextHolder = null;

    if (description) {
      itemTextHolder = $('<div></div>')
          .addClass('carousel-item-text-holder ' + this.styles.description);
      itemTextHolder.append(description);
    }

    var item = $('<div></div>')
        .addClass('carousel-item ' + this.styles.normal).append(content);

    if (typeof addCallback == 'function') {
      addCallback(item, navData);
    }

    if (navData) {
      item.data("nav-data", navData);
    }

    var itemDiv = $('<div></div>')
        .addClass('carousel-item-div ' + this.styles.itemDiv)
        .append(item);

    if (description) {
      itemDiv.append(itemTextHolder);
    }

    this.container.append(itemDiv);
  }

  var carousel = this;

  var keyMapping = {
    13: function(selectedItem, newItem) {  // enter
      carousel.activateItem(selectedItem);
      return { status: 'none' };
    },
    37: function(selectedItem, newItem) {  // left
      if (newItem.length == 0) {
        newItem = carousel.container.find('.carousel-item').last();
        return { status: 'selected', selected: newItem };
      }
      return { status: 'none' };
    },
    39: function(selectedItem, newItem) {  // right
      if (newItem.length == 0) {
        newItem = carousel.container.find('.carousel-item').first();
        return { status: 'selected', selected: newItem };
      }
      return { status: 'none' };
    }
  };

  var actions = {
    scrollIntoView: function(selectedItem, newItem, getFinishCallback) {
      carousel.selectItem(selectedItem, newItem, getFinishCallback);
    },
    click: function(selectedItem, newItem) {
      carousel.activateItem(selectedItem);
    },
    enterZone: function() {
      if (typeof carousel.callbacks.onFocus == 'function') {
        carousel.callbacks.onFocus();
      }
    },
    leaveZone: function() {
      if (typeof carousel.callbacks.onBlur == 'function') {
        carousel.callbacks.onBlur();
      }
    }
  };

  var navSelectors = {
    item: '.carousel-item',
    itemParent: '.carousel-item-div',
    itemRow: '.carousel-control',
    itemPage: '.carousel-control'
  };

  var selectionClasses = {
    basic: this.styles.selected
  };

  var zoneParms = {
    containerSelector: this.parentSelector,
    keyMapping: keyMapping,
    actions: actions,
    navSelectors: navSelectors,
    selectionClasses: selectionClasses,
    navigableData: 'nav-data'
  };

  this.behaviorZone = new gtv.jq.KeyBehaviorZone(zoneParms);
  this.keyController.addBehaviorZone(this.behaviorZone, true, this.layers);

  if (this.behaviors.selectOnInit) {
    this.activateItem(this.container.find('.carousel-item').first());
  }

  return true;
};

/**
 * Returns if the Carousel is visible or not.
 * @return {boolean} true if the Carousel is visible
 */
gtv.jq.Carousel.prototype.isVisible = function() {
  if (this.topParent) {
    return this.topParent.is(':visible');
  }
  return false;
};

/**
 * Call the onBeforeScroll callback in case it's defined.
 */
gtv.jq.Carousel.prototype.callOnBeforeScroll = function() {
  this.topParent.stop();

  if (typeof this.callbacks.onBeforeScroll == 'function') {
    this.callbacks.onBeforeScroll();
  }
};

/**
 * Switch the selectedItem css classes.
 * @param {jQuery.Element} the item to be selected.
 */
gtv.jq.Carousel.prototype.updateSelectionClasses = function(newItem) {
  if (this.selectedItem) {
    this.selectedItem.removeClass(this.styles.selected);
  }
  newItem.addClass(this.styles.selected);
};

/**
 * Sets the item as active, calling the onActivate callback if defined.
 * @param {jQuery.Element} the item to be activated.
 */
gtv.jq.Carousel.prototype.activateItem = function(item) {
  if (!item) {
    return;
  }

  if (this.activeItem) {
    this.activeItem.removeClass(this.styles.chosen);
  }

  if (typeof this.callbacks.onActivated == 'function') {
    this.callbacks.onActivated(item);
    this.selectedItem = item;
    this.activeItem = item;
    this.activeItem.addClass(this.styles.chosen);
  }
};

/**
 * Selects next Carousel item.
 * @param {boolean} true if the item should be activated after selection.
 */
gtv.jq.Carousel.prototype.selectNext = function(activate) {
  var carousel = this;

  if (this.selectedItem) {
    var newItem = this.selectedItem
        .parent()
        .nextAll('.carousel-item-div')
        .eq(0)
        .find('.carousel-item');
    if (newItem && newItem.length == 0) {
      newItem = this.container.find('.carousel-item').first();
    }
    this.selectItem(this.selectedItem, newItem, function() {
      carousel.updateSelectionClasses(newItem);
      if (activate) {
        carousel.activateItem(newItem);
      }
    });
  }
};

/**
 * Selects previous Carousel item.
 * @param {boolean} true if the item should be activated after selection.
 */
gtv.jq.Carousel.prototype.selectPrevious = function(activate) {
  var carousel = this;

  if (this.selectedItem) {
    var newItem = this.selectedItem
        .parent()
        .prevAll('.carousel-item-div')
        .eq(0)
        .find('.carousel-item');
    if (newItem && newItem.length == 0) {
      newItem = this.container.find('.carousel-item').last();
    }
    this.selectItem(this.selectedItem, newItem, function() {
      carousel.updateSelectionClasses(newItem);
      if (activate) {
        carousel.activateItem(newItem);
      }
    });
  }
};

/**
 * Selects a Carousel item, scrolling if necesary.
 * @param {jQuery.Element} current selected item.
 * @param {jQuery.Element} new selected item.
 * @param {SynchronizedCallback.acquireCallback} callback to be called once the Carousel
 *     scrolling ends.
 */
gtv.jq.Carousel.prototype.selectItem = function(selectedItem,
                                                newItem,
                                                getFinishCallback) {
  if (!newItem) {
    return;
  }

  if (!selectedItem) {
    selectedItem = this.container.find('.carousel-item').first();
  }

  var selectedIndex = selectedItem.data('index');
  var newIndex = newItem.data('index');

  var carousel = this;

  var onFinishScroll = function() {
    if (typeof carousel.callbacks.onSelected == 'function') {
      carousel.callbacks.onSelected(newItem);
    }
    var finishCallback = getFinishCallback();
    if (typeof finishCallback == 'function') {
      finishCallback();
    }
    carousel.selectedItem = newItem;
  };

  // May need to scroll
  if (this.behaviors.itemsToDisplay < this.items.length) {
    if (newIndex == 0) { // Scrolling to first
      this.callOnBeforeScroll();
      this.topParent.animate({ scrollLeft: 0 }, onFinishScroll);
    } else {
      var newItemLeft = newItem.position().left
          - parseInt(newItem.parent().css("padding-left"))
              - parseInt(newItem.parent().css("margin-left"));

      var newItemRight = newItem.position().left + newItem.width()
          + parseInt(newItem.parent().css("padding-right"))
              + parseInt(newItem.parent().css("margin-right"));

      var parentLeft = this.topParent.position().left
          + parseInt(this.topParent.css("margin-left").replace("px", ""))
              + parseInt(this.topParent.css("padding-left").replace("px", ""));

      var parentRight = parentLeft
          + this.topParent.width()
              - parseInt(this.topParent.css("margin-right").replace("px", ""))
                  - parseInt(
                      this.topParent.css("padding-right").replace("px", ""));
      if (newItemLeft < parentLeft ||
          newItemRight > parentRight) { // Need to scroll left or right
        this.callOnBeforeScroll();
        var scrollDelta = newIndex > selectedIndex ?
            (newItemRight - parentRight) : (newItemLeft - parentLeft);

        this.topParent.animate({
            scrollLeft: this.topParent.scrollLeft() + scrollDelta
          }, onFinishScroll);
      }
      else { // No need to scroll
        onFinishScroll();
      }
    }
  }
  else { // No need to scroll
    onFinishScroll();
  }
};
