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
 * @fileoverview Common classes used throughout the library. GtvCore contains
 *     public static methods for processing feeds. SynchronizedCallback
 *     can be used to aggregate multiple asynch callback events into a single
 *     call.
 * 
 */

var gtv = gtv || {
  jq: {}
};


/**
 * Static class for utilities used by controls
 * @constructor
 * @private
 */
gtv.jq.GtvCore = function() {
};

/**
 * Triggers a 'load' event on a container when images have finished loading
 * @param {jQuery.Element} container Container to trigger after images load.
 *     If images not supplied, the container will be triggered when images
 *     in it have finished loading.
 * @param {?Array.<jQuery.Element>} images Optional image elements.
 *     Supply this if container is to be triggered on images that aren't
 *     descendants of it.
 * @private
 */
gtv.jq.GtvCore.triggerOnLoad = function(container, images) {
  images = images || container.find('img');
  var imgCount = images.length;

  if (imgCount == 0) {
    container.trigger('load');
    return;
  }

  images.each(function(index) {
    if ($(this).complete) {
      imgCount--;
      if (imgCount == 0) {
        container.trigger('load');
      }
    } else {
      images.load(function() {
        imgCount--;
        if (imgCount == 0) {
          container.trigger('load');
        }
      });
    }
  });
};


/**
 * Creates a function to retrieve the next item from an item parameter,
 * which may be a generator function or an array.
 * @param {ControlContents} controlContents A ControlContents object with either
 *     an items attribute or an itemsGenerator attribute set.
 * @return {function(jQuery.Element)} A function adds the next item in a
 *     collection to the supplied container.
 * @private
 */
gtv.jq.GtvCore.makeAddNextItemParams = function(controlContents) {
  var addNextItem;
  if (controlContents.itemsGenerator) {
    // If a generator is specified, the return function is a pass-through that
    // calls the generator. (This generator creates an item, adds it to the
    // parent and returns true; or returns false if it has no item to add.)
    addNextItem = function(parent) {
      return controlContents.itemsGenerator(parent);
    };
  } else if (controlContents.items) {
    // If an items array is specified, return a function that adds the next
    // item in the array to the parent and returns true; or returns false if
    // the end of the array has been reached.
    var index = 0;
    addNextItem = function(parent) {
      if (index >= controlContents.items.length) {
        return false;
      }

      var item = controlContents.items[index];
      if (!item) {
        return false;
      }

      index++;
      parent.append(item);
      return true;
    };
  }
  return addNextItem;
};

/**
 * Reads a feed in ATOM format and makes callbacks to build an array of
 * items from the feed.
 * @param {string} feed URL to the feed to read.
 * @param {function(Object)} makeItem A callback function that, when passed
 *     an entry from the feed returns a constructed item from it.
 * @param {function(Array.<Object>)} doneCallback A callback that will be passed
 *     the array of all constructed items.
 * @private
 */
gtv.jq.GtvCore.processAtomFeed = function(feed, makeItem, doneCallback) {
  $.ajax({
    url: feed,
    success: function(data) {
      var itemsArray = [];

      var entries = $(data).find('entry');
      for (var i = 0; i < entries.length; i++) {
        var item = makeItem(entries[i]);
        if (item) {
          itemsArray.push(item);
        }
      }
      doneCallback(itemsArray);
    }
  });
};

/**
 * Reads a feed in JSONP format and makes callbacks to build an array of
 * items from the feed.
 * @param {string} feed URL to the feed to read.
 * @param {function(Object)} makeItem A callback function that, when passed
 *     an entry from the feed returns a constructed item from it.
 * @param {function(Array.<Object>)} doneCallback A callback that will be passed
 *     the array of all constructed items.
 * @param {Array.<string>)} entryKey An array of strings that represent, in
 *     hierarchical order the path to the array of entries in the returned feed.
 * @private
 */
gtv.jq.GtvCore.processJsonpFeed = function(feed,
                                           makeItem,
                                           doneCallback,
                                           entryKey) {
  entryKey = entryKey || ['feed', 'entry'];

  $.ajax({
    url: feed,
    dataType: 'jsonp',
    success: function(data) {
      var itemsArray = [];

      var entries = data;
      for (var j = 0; j < entryKey.length; j++)
        entries = entries[entryKey[j]];

      for (var i = 0; i < entries.length; i++) {
        var item = makeItem(entries[i]);
        if (item) {
          itemsArray.push(item);
        }
      }

      doneCallback(itemsArray);
    }
  });
};

gtv.jq.GtvCore.doAjaxCall = function(url, dataType, jsonpCallback, callbackSuccess, callbackError) {
  var options = {
    url: url,
    dataType: dataType,
    error: function(httpRequest, textStatus, errorThrown){
      callbackError(errorThrown);
    },
    success: function(data, textStatus, httpRequest){
      callbackSuccess(data);
    }
  };
  if (dataType == 'jsonp') {
    options.jsonpCallback = jsonpCallback;
  }
  return $.ajax(options);
};

gtv.jq.GtvCore.getZoom = function() {
  var zoom = parseFloat($(document.body).css('zoom'));
  if (isNaN(zoom)) {
    zoom = 1;
  }
  return zoom;
};

gtv.jq.GtvCore.getInt = function(value) {
  value = parseInt(value);
  if (isNaN(value)) {
    value = 0;
  }

  return value;
};

gtv.jq.GtvCore.preloadImages = function(images) {
  var img = new Image();
  for(var i=0; i<images.length; i++) {
    img.src = images[i];
  }
};

gtv.jq.GtvCore.formatTime = function(seconds, unit) {
  function padCero(num) {
    if (num < 10) {
      return '0' + num;
    }
    return num.toString();
  }

  switch (unit) {
    case 'hours': {
      var hours = Math.floor(seconds / 3600);
      var minutes = Math.floor(seconds % 3600);
      return padCero(hours) + ':' + gtv.jq.GtvCore.formatTime(minutes, 'minutes');
    }
    case 'minutes': {
      var minutes = Math.floor(seconds / 60);
      seconds = Math.floor(seconds % 60);
      return padCero(minutes) + ':' + gtv.jq.GtvCore.formatTime(seconds, 'seconds');
    }
    case 'seconds': {
      return padCero(seconds);
    }
  }
  return padCero(seconds);
};


/**
 * A class that tracks by reference count a number of requests for a single
 * callback and makes sure that it is called once when all requests are
 * completed. The constructor starts the count at 1 and expects this to be
 * cleared by the creator calling done().
 * @constructor
 * @param {function} callback The callback to make when all dependent requests
 *     are completed.
 * @private
 */
gtv.jq.SynchronizedCallback = function(callback) {
  this.expectedCallbacks = 1;
  this.callback = callback;
};

/**
 * Called to acquire a reference to the callback.
 * @return {function} The callback function to make when a depedent request is
 *     completed.
 */
gtv.jq.SynchronizedCallback.prototype.acquireCallback = function() {
  var synchronizedCallback = this;

  synchronizedCallback.expectedCallbacks++;
  return function() {
    synchronizedCallback.callbackFinished();
  };
};

/**
 * Creates a wrapper callback for acquiring a callback
 * @return {function} A function that can be called to acquire the callback
 *     without access to the object instance.
 */
gtv.jq.SynchronizedCallback.prototype.getCallback = function() {
  var synchronizedCallback = this;

  return function() {
    return synchronizedCallback.acquireCallback();
  };
};

/**
 * Decrements the callback reference count and calls the primary callback
 * if all dependent callbacks are completed.
 * @private
 */
gtv.jq.SynchronizedCallback.prototype.callbackFinished = function() {
  this.expectedCallbacks--;
  if (this.expectedCallbacks == 0 && this.callback)
    this.callback();
};

/**
 * Called by the code that originally constructed the object instance to
 * represent that it is finished initiating tasks with dependent callbacks.
 */
gtv.jq.SynchronizedCallback.prototype.done = function() {
  this.callbackFinished();
};


/**
 * Holds parameters used to create the library controls.
 * @param {?gtv.jq.CreationParams} opt_params CreationParams to initialize
 *     this new object with.
 * @constructor
 */
gtv.jq.CreationParams = function(opt_params) {
  var params = opt_params || {};

  params.styles = params.styles || {};
  this.styles = params.styles;
  this.styles.page = params.styles.page || '';
  this.styles.row = params.styles.row || '';
  this.styles.itemDiv = params.styles.itemDiv || '';
  this.styles.item = params.styles.item || '';
  this.styles.selected = params.styles.selected || 'item-hover';
  this.styles.hasData = params.styles.hasData || 'item-hover-active';
  this.styles.normal = params.styles.normal || '';
  this.styles.chosen = params.styles.chosen || '';

  this.containerId = params.containerId;
  if (!this.containerId) {
    throw new Error('containerId must be provided');
  }

  this.choiceCallback = params.choiceCallback ||
    function() {
    };

  this.layerNames = params.layerNames;

  this.keyController = params.keyController;
};

/**
 * Instance of the key controller this control is using.
 * @type {KeyController}
 */
gtv.jq.CreationParams.prototype.keyController = null;

/**
 * CSS classes used to style the row.
 *     page {string} CSS class to style the container for each page of rows.
 *     row {string} CSS class to style the row.
 *     itemsDiv {string} CSS class to style the DIV holding the items.
 *     itemDiv {string} CSS class to style the DIV holding a single item.
 *     item {string} CSS class to style the individual item.
 *     selected {string} CSS class to style the item that has the selection.
 *     hasData {string} CSS class to style the item that has the selection,
 *         for controls that support different selection styles based on
 *         associated data (see gtv.jq.CaptionItem).
 *     normal {string} For controls that maintain a sticky item choice, such
 *         as SideNav. CSS class to style an item that has been 'chosen', that
 *         is, the ENTER key was pressed while it had selection, or it
 *         received a mouse click.
 *     chosen {string}  For controls that maintain a sticky item choice, such
 *         as SideNav. CSS class to style an item that has been 'chosen', that
 *         is, the ENTER key was pressed while it had selection, or it
 *         received a mouse click.
 * @type Object
 */
gtv.jq.CreationParams.prototype.styles = null;

/**
 * The ID of the control container (an element will be created with this ID).
 * @type string
 */
gtv.jq.CreationParams.prototype.containerId = null;

/**
 * Callback to make when the user chooses an item (if applicable to the control)
 * @type Function(selectedItem)
 */
gtv.jq.CreationParams.prototype.choiceCallback = null;

/**
 * Array of Layer name to add the control to, or 'default' if not supplied.
 * @type string
 */
gtv.jq.CreationParams.prototype.layerNames = null;


/**
 * Describes an item that has a caption and a data item to go with it.
 * Not all controls support CaptionItem (StackControl, SlidingControl).
 * Use this instead of a simple items array when an item that needs
 * selection (say, a thumbnail) also needs a caption (say, photo title)
 * but the selection outline should only be drawn around the item.
 * @constructor
 */
gtv.jq.CaptionItem = function() {
};

/**
 * The item that will be outlined by selection. This will be the child of
 * the element with the CSS class styles.item.
 * @type jQuery.Element
 */
gtv.jq.CaptionItem.prototype.item = null;

/**
 * The caption for the item, to be displayed beneath it. The container of this
 * caption will be styled so that it will be clipped at the width of the item.
 * @type jQuery.Element
 */
gtv.jq.CaptionItem.prototype.caption = null;

/**
 * If supplied, this item will be given an active hover style by the key
 * controller when selected. This allows items with data to be visually
 * distinguished from those without. For example, an item that can be
 * navigated to when chosen might have this value non-null; and item that
 * cannot will have it null. The two different selection styles applied
 * (styles.selected, styles.hasData) provide a visual clue to the user.
 */
gtv.jq.CaptionItem.prototype.data = null;


/**
 * Describes the contents to be added to a control. Passed with ShowParams
 * object, used when calling showControl on a control object.
 *
 * items, itemsArray and itemsGenerator, indicate how new items will be
 * added to the control being displayed. Only one of these should be supplied
 * in an instance of the object.
 * @param {gtv.jq.ControlContents} opt_params Optional initialization values.
 * @constructor
 */
gtv.jq.ControlContents = function(opt_params) {
  var params = opt_params || {};

  this.items = params.items;
  this.captionItems = params.captionItems;
  this.contentsArray = params.contentsArray;
  this.itemsGenerator = params.itemsGenerator;
};

/**
 * Simple array of items to add to the control. These items will be added to
 * the control in the order they appear in the array. Each item is added as
 * a child of a separate Element to contain it. These container elements are
 * created by the control and given the Styles.item CSS class.
 * @type Array.<jQuery.Element>
 */
gtv.jq.ControlContents.prototype.items = null;

/**
 * Simple array of items to add to the control. These items will be added to
 * the control in the order they appear in the array. Each item is added as
 * a child of a separate Element to contain it. These container elements are
 * created by the control and given the Styles.item CSS class.
 * @type Array.<gtv.jq.CaptionItem>
 */
gtv.jq.ControlContents.prototype.captionItems = null;

/**
 * Array of ControlContents objects to add to a control. Some multi-row
 * controls (such as the RollerControl) require this so that each row can be
 * described explicitly. That is, each row has a very specific contents
 * instead of being created as-needed and filled in.
 *
 * Since this is an array of ControlContents objects, each element is can
 * in turn be a simple array of items or an itemsGenerator. (It could also
 * take an itemsArray, but no existing controls take an array of arrays of
 * arrays.)
 * @type Array.<gtv.jq.ControlContents>
 */
gtv.jq.ControlContents.prototype.contentsArray = null;

/**
 * A function that generates items as-requested. Clients creating controls
 * can use this to create one or more controls in a callback instead of having
 * them pre-created an placed in an items array. Generally this callback
 * maintains state in its closure and creates the each subsequent item in a
 * collection when it is called. This function also must add its control to
 * the parent element, which is passed in. The parent element is already in
 * the page DOM when the callback is called, so controls added to the parent
 * will be in the DOM immediately as well.
 *
 * This function should return boolean true if it added an element to the
 * parent, and false if it did not (and has no further elements to add).
 * @type Function(jQuery.Element)
 */
gtv.jq.ControlContents.itemsGenerator = null;

/**
 * Holds parameters used to show the library controls.
 * @param {?gtv.jq.ShowParams} opt_params Optional parameters to initialize the
 *     new object with.
 * @constructor
 */
gtv.jq.ShowParams = function(opt_params) {
  var params = opt_params || {};

  this.topParent = params.topParent;
  if (!this.topParent) {
    throw new Error("topParent must be supplied.");
  }

  this.contents = new gtv.jq.ControlContents(params.contents);
};

/**
 * Parent element on the page that holds the control.
 * @type jQuery.Element
 */
gtv.jq.ShowParams.prototype.topParent = null;

/**
 * The contents the control should have. See gtv.jq.ControlContents for
 * details.
 * @type gtv.jq.ControlContents
 */
gtv.jq.ShowParams.prototype.contents = null;


/**
 * Size class holds a width/height dimension pair.
 * @param {number} width
 * @param {number} height
 * @constructor
 */
gtv.jq.Size = function(width, height) {
  this.width = width;
  this.height = height;
};

/**
 * Width dimension in pixels.
 * @type number
 */
gtv.jq.Size.prototype.width;

/**
 * Height dimension in pixels.
 * @type number
 */
gtv.jq.Size.prototype.height;

