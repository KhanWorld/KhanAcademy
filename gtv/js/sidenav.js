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
 * @fileoverview Classes for SideNavControl
 * 
 */

var gtv = gtv || {
  jq: {}
};

/**
 * SideNavParams class holds configuration values specific to SideNav.
 * @param {gtv.jq.SideNavParams} opt_params Optional initialization values.
 * @constructor
 */
gtv.jq.SideNavParams = function(opt_params) {
  var params = opt_params || {};

  this.behaviors = new gtv.jq.SideNavBehaviors(params.behaviors);
  this.createParams = new gtv.jq.CreationParams(params.createParams);
};

/**
 * CreationParams for the SideNav control.
 * @type CreationParams
 */
gtv.jq.SideNavParams.prototype.createParams = null;

/**
 * Behaviors for the SideNav control.
 * @type SideNavBehaviors
 */
gtv.jq.SideNavParams.prototype.behaviors = null;


/**
 * SideNavBehaviors configures the behaviors for a SideNav control.
 * @param {gtv.jq.SideNavBehaviors} opt_behaviors Optional initial values.
 * @constructor
 */
gtv.jq.SideNavBehaviors = function(opt_behaviors) {
  var behaviors = opt_behaviors || {};

  this.orientation = behaviors.orientation || 'vertical';
  this.popOut = behaviors.popOut || '';
  this.fade = behaviors.fade || '';
  this.selectOnInit = behaviors.selectOnInit || false;
};

/**
 * Tells the SideNav control how to orient itself: 'vertical' (default) or
 * 'horizontal'
 * @type string
 */
gtv.jq.SideNavBehaviors.prototype.orientation;

/**
 * Tells the SideNav control to pop out from a side. One of: 'left', 'right',
 * 'top', 'bottom'.
 * @type string
 */
gtv.jq.SideNavBehaviors.prototype.popOut;

/**
 * If true, tells the SideNav control to fade in/out when selection moves to it.
 * @type boolean
 */
gtv.jq.SideNavBehaviors.prototype.fade;

/**
 * If true, the first item in the SideNav menu will be 'chosen' when the
 * control is shown.
 * @type boolean
 */
gtv.jq.SideNavBehaviors.prototype.selectOnInit;


/**
 * SideNavControl class. SideNav control is a pop-out or fade-in menu control
 * that can manage selection or contain other controls.
 * @param {gtv.jq.SideNavParams} sidenavParams
 * @constructor
 */
gtv.jq.SideNavControl = function(sidenavParams) {
  this.params_ = new gtv.jq.SideNavParams(sidenavParams);
};

/**
 * Parent element containing the control elements.
 * @type jQuery.Element
 * @private
 */
gtv.jq.SideNavControl.prototype.container_ = null;

/**
 * Collection of menu-item rows in the sidenav control.
 * @type Array.<jQuery.Element>
 * @private
 */
gtv.jq.SideNavControl.prototype.rows_ = null;

/**
 * Holds the params the control was created with.
 * @type CreationParams
 * @private
 */
gtv.jq.SideNavControl.prototype.params_ = null;

/**
 * Holds the params for showing the control.
 * @type ShowParams
 * @private
 */
gtv.jq.SideNavControl.prototype.showParams_ = null;

/**
 * Key controller behavior zone for this control.
 * @type KeyBehaviorZone
 * @private
 */
gtv.jq.SideNavControl.prototype.behaviorZone_ = null;

/**
 * Moves selection to the SideNav Control.
 */
gtv.jq.SideNavControl.prototype.selectControl = function() {
  var sideNavControl = this;

  sideNavControl.params_.createParams.keyController.setZone(
      sideNavControl.behaviorZone_,
      true);
};

/**
 * Removes the control from its container and its key control zone.
 */
gtv.jq.SideNavControl.prototype.deleteControl = function() {
  var sideNavControl = this;

  sideNavControl.params_.createParams.keyController.removeBehaviorZone(
    sideNavControl.behaviorZone_);
  sideNavControl.container_.remove();
};

/**
 * Creates a new SideNavControl with the specified items and adds it to a
 * container_ on the page.
 * @param {gtv.jq.ShowParams} showParams Params for creating the control.
 */
gtv.jq.SideNavControl.prototype.showControl = function(showParams) {
  var sideNavControl = this;

  sideNavControl.showParams_ = new gtv.jq.ShowParams(showParams);

  sideNavControl.container_ = $('<div></div>');
  sideNavControl.container_.addClass('sidenav-container')
    .attr('id', sideNavControl.params_.createParams.containerId);
  sideNavControl.showParams_.topParent.append(sideNavControl.container_);

  sideNavControl.rows_ = $('<div></div>').addClass('sidenav-rows');
  sideNavControl.container_.append(sideNavControl.rows_);

  var addNextItem =
    gtv.jq.GtvCore.makeAddNextItemParams(sideNavControl.showParams_.contents);
  if (!addNextItem) {
    throw new Error('SideNavControl requires either items or itemsGenerator');
  }

  var firstItem;
  var j = 0;
  // This loop adds items to the sidenav menu. It continues to add until the
  // addNextItem() function (generated above) returns false, signalling that
  // no new items are available to add.
  while (true) {
    var itemRow;
    if (!itemRow ||
        sideNavControl.params_.behaviors.orientation == 'vertical') {
      itemRow = $('<div></div>').addClass('sidenav-item-row ' +
          sideNavControl.params_.createParams.styles.row);
      sideNavControl.rows_.append(itemRow);
    }

    var itemDiv = $('<div></div>').addClass('sidenav-item-div ' +
        sideNavControl.params_.createParams.styles.itemDiv);
    if (sideNavControl.params_.behaviors.orientation == 'horizontal')
      itemDiv.css('float', 'left');
    itemRow.append(itemDiv);

    var item = $('<div></div>')
      .addClass('sidenav-item ' +
                sideNavControl.params_.createParams.styles.normal
                + ' ' + sideNavControl.params_.createParams.styles.item)
      .data('index', j);
    itemDiv.append(item);

    if (!firstItem || j == showParams.highlightedCategoryIndex)
      firstItem = item;

    if (!addNextItem(item)) {
      itemDiv.remove();
      if (sideNavControl.params_.behaviors.orientation == 'vertical')
        itemRow.remove();
      break;
    }

    j++;
  }

  sideNavControl.setBehaviors(sideNavControl.params_.behaviors, true);

  var keyMapping = {
    // enter key calls the chosenAction callback provided by the control client.
    13: function(selectedItem, newSelected) {
      sideNavControl.handleChosenAction_(selectedItem);
      return new gtv.jq.Selection('skip');
    },
    38: function(selectedItem, newSelected) {
      if( !newSelected[0] ) { // test if it's input or menu items
        $('#keyword').focus();
        $('#keyword').val(' ');
        $('#keyword').removeClass('keyword-hint').addClass('keyword-text');
      }
      return new gtv.jq.Selection('none');
    },
  };
  var navSelectors = {
    item: '.sidenav-item',
    itemParent: '.sidenav-item-div',
    itemRow: '.sidenav-item-row'
  };
  var selectionClasses = {
    basic: sideNavControl.params_.createParams.styles.selected
  };
  var actions = {
    // click calls the chosenAction callback provided by the control client.
    click: function(selectedItem, newItem) {
      sideNavControl.handleChosenAction_(selectedItem);
    },
    // When entering the zone for this control, animate the nav bar into view
    // as appropriate (scroll in from sides, or fade in)
    enterZone: function() {
      return sideNavControl.handleEnterZone_();
    },
    // When leaving the zone for this control, animate the nav bar out of view
    // as appropriate (scroll out to sides, or fade out)
    leaveZone: function() {
      sideNavControl.handleLeaveZone_();
    }
  };

  sideNavControl.behaviorZone_ =
      new gtv.jq.KeyBehaviorZone({
        containerSelector: '#' +
            sideNavControl.params_.createParams.containerId,
        keyMapping: keyMapping,
        actions: actions,
        navSelectors: navSelectors,
        selectionClasses: selectionClasses
      });

  sideNavControl.params_.createParams.keyController.addBehaviorZone(
    sideNavControl.behaviorZone_,
    true,
    sideNavControl.params_.createParams.layerNames);

  if (sideNavControl.params_.behaviors.selectOnInit) {
    sideNavControl.handleChosenAction_(firstItem);
  }
};

/**
 * Shows the control, if approprate, when the zone for this control is
 * entered.
 * @return {jQuery.Element} The item in the zone that should be selected
 *     upon entry. In this case, we start with the chosen nav item.
 * @private
 */
gtv.jq.SideNavControl.prototype.handleEnterZone_ = function() {
  var sideNavControl = this;

  if (sideNavControl.params_.behaviors.popOut) {
    sideNavControl.container_.css({
        '-webkit-transition': 'all 1s ease-in-out'
      });
    if (sideNavControl.params_.behaviors.popOut == 'left') {
      sideNavControl.container_.css({
        left: '0px'
      });
    } else if (sideNavControl.params_.behaviors.popOut == 'right') {
      var windowWidth = $(window).width();
      var width = sideNavControl.container_.outerWidth(true);
      sideNavControl.container_.css({
            left: (windowWidth - width) + 'px'
          });
    } else if (sideNavControl.params_.behaviors.popOut == 'top') {
      sideNavControl.container_.css({
          top: '0px'
        });
    } else if (sideNavControl.params_.behaviors.popOut == 'bottom') {
      var windowHeight = $(window).height();
      var height = sideNavControl.container_.outerHeight(true);
      sideNavControl.container_.css({
          top: (windowHeight - height) + 'px'
        });
    }
  } else if (sideNavControl.params_.behaviors.fade) {
    sideNavControl.container_.css({
        '-webkit-transition': 'all 1s ease-in-out'
      });

    sideNavControl.container_.css({
        opacity: '1.0'
      });
  }
  return sideNavControl.chosenItem;
};

/**
 * Hides the control, if approprate, when the zone for this control is
 * exited.
 * @private
 */
gtv.jq.SideNavControl.prototype.handleLeaveZone_ = function() {
  var sideNavControl = this;

  if (sideNavControl.params_.behaviors.popOut) {
    sideNavControl.container_.css({
        '-webkit-transition': 'all 1s ease-in-out'
      });
    if (sideNavControl.params_.behaviors.popOut == 'left') {
      var width = sideNavControl.container_.outerWidth(true);
      sideNavControl.container_.css({
          left: (-width) + 'px'
        });
    } else if (sideNavControl.params_.behaviors.popOut == 'right') {
      var windowWidth = $(window).width();
      sideNavControl.container_.css({
          left: (windowWidth) + 'px'
        });
    } else if (sideNavControl.params_.behaviors.popOut == 'top') {
      var height = sideNavControl.container_.outerHeight(true);
      sideNavControl.container_.css({
          top: (-height) + 'px'
        });
    } else if (sideNavControl.params_.behaviors.popOut == 'bottom') {
      var windowHeight = $(window).height();
      sideNavControl.container_.css({
          top: (windowHeight) + 'px'
        });
    }
  } else if (sideNavControl.params_.behaviors.fade) {
    sideNavControl.container_.css({
        '-webkit-transition': 'all 1s ease-in-out'
      });
    sideNavControl.container_.css({
        opacity: '0'
      });
  }
};


/**
 * Applies a new set of behaviors to the control.
 * @param {Object} behaviors New behaviors to apply to the control.
 * @param {boolean} force Set the new behaviors even if identical.
 */
gtv.jq.SideNavControl.prototype.setBehaviors = function(behaviors, force) {
  var sideNavControl = this;

  if (!force && behaviors === sideNavControl.params_.behaviors) {
    return;
  }

  sideNavControl.params_.behaviors = behaviors || {};

  var height = sideNavControl.rows_.height();
  var width = sideNavControl.rows_.width();
  sideNavControl.container_.css({ height: height + 'px',
                                 width: width + 'px'});

  if (behaviors.popOut) {
    // If this is a popout nav bar from the side, position the container at
    // its starting point off the page, based on the side of the page it is
    // popping out of.
    if (behaviors.popOut == 'left') {
      var containerWidth = sideNavControl.container_.outerWidth(true);
      sideNavControl.container_.css({
        position: 'absolute',
        left: (-containerWidth) + 'px'
      });
    } else if (behaviors.popOut == 'right') {
      var windowWidth = $(window).width();
      sideNavControl.container_.css({
        position: 'absolute',
        left: (windowWidth) + 'px'});
    } else if (behaviors.popOut == 'top') {
      var containerHeight = sideNavControl.container_.outerHeight(true);
      sideNavControl.container_.css({
        position: 'absolute',
        top: (-containerHeight) + 'px'
      });
    } else if (behaviors.popOut == 'bottom') {
      var windowHeight = $(window).height();
      sideNavControl.container_.css({
        position: 'absolute',
        top: (windowHeight) + 'px'
      });
    }

    // Add a semi-opaque backdrop under the nav var when its popped out for
    // visual clarity.
    var backdrop = sideNavControl.container_.children('.sidenav-backdrop');
    if (backdrop.length == 0) {
      backdrop = $('<div></div>').addClass('sidenav-backdrop');
      sideNavControl.container_.prepend(backdrop);
    }

    sideNavControl.rows_.css('position', 'absolute');
  } else if (behaviors.fade) {
    // If this is a fade-in nav bar, set its opacity to 0 to start.
    sideNavControl.rows_.css('position', 'absolute');
    sideNavControl.container_.css({
      opacity: '0'
    });
  } else {
    // If the nav menu is neither popout or fade-in, it's statically positioned.
    var backdrop = sideNavControl.container_.find('.sidenav-backdrop');
    backdrop.remove();
    sideNavControl.rows_.css('position', 'static');
  }
};

/**
 * Event handler for click or <enter> keypress. Moves the chosen style if
 * supplied, and makes choice callback if supplied.
 * @param {jQuery.Element} selectedItem The item that received the event.
 * @private
 */
gtv.jq.SideNavControl.prototype.handleChosenAction_ = function(selectedItem) {
  var sideNavControl = this;

  if (sideNavControl.params_.createParams.styles.chosen) {
    if (sideNavControl.chosenItem) {
      sideNavControl.chosenItem.removeClass(
          sideNavControl.params_.createParams.styles.chosen);
      sideNavControl.chosenItem.addClass(
        sideNavControl.params_.createParams.styles.normal);
    }
    selectedItem.removeClass(sideNavControl.params_.createParams.styles.normal);
    selectedItem.addClass(sideNavControl.params_.createParams.styles.chosen);
  }

  sideNavControl.chosenItem = selectedItem;

  if (sideNavControl.params_.createParams.choiceCallback) {
    sideNavControl.params_.createParams.choiceCallback(selectedItem);
  }
};

