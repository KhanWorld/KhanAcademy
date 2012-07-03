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
 * @fileoverview Classes for Tooltip Control
 *
 * 
 */

var gtv = gtv || {
  jq: {}
};

/**
 * TooltipParams class holds configuration values specific to Tooltip.
 * @constructor
 */
gtv.jq.TooltipParams = function() {
};

/**
 * CreateParams for the Tooltip control.
 * @type {CreateParams}
 */
gtv.jq.TooltipParams.prototype.createParams = null;

/**
 * Behaviors for the Tooltip control.
 * @type {TooltipBehaviors}
 */
gtv.jq.TooltipParams.prototype.behaviors = null;

/**
 * TooltipBehaviors configures the behaviors for a Tooltip control.
 * @constructor
 */
gtv.jq.TooltipBehaviors = function() {
};

/**
 * Tells the Tooltip if it will be showed using an animation.
 * @type {boolean}
 */
gtv.jq.TooltipBehaviors.prototype.animate = null;

/**
 * Tells the Tooltip the milliseconds the animation will take.
 * @type {number}
 */
gtv.jq.TooltipBehaviors.prototype.showDuration = null;

/**
 * Tells the Tooltip the milliseconds the animation will take.
 * @type {number}
 */
gtv.jq.TooltipBehaviors.prototype.duration = null;

/**
 * Sets the background color for the Tooltip.
 * @type {string}
 */
gtv.jq.TooltipBehaviors.prototype.bgColor = null;

/**
 * Sets the border color for the Tooltip.
 * @type {string}
 */
gtv.jq.TooltipBehaviors.prototype.borderColor = null;

/**
 * Sets the corners radius for the Tooltip.
 * @type {number}
 */
gtv.jq.TooltipBehaviors.prototype.radius = null;

/**
 * Sets the glowPadding for the Tooltip.
 * @type {number}
 */
gtv.jq.TooltipBehaviors.prototype.glowPadding = null;

/**
 * Tooltip class. Tooltip control display text in a tooltip
 * shape component.
 * @param {gtv.jq.TooltipParams} tooltipParms
 * @constructor
 */
gtv.jq.Tooltip = function(tooltipParms)
{
  this.params_ = jQuery.extend(tooltipParms.createParams, tooltipParms);

  this.holder = this.params_.topParent;
  this.containerId = this.params_.containerId;
  this.styles = this.params_.styles || {
    containerClass: 'tooltip',
    leftDescClass: 'floatLeft',
    rightDescClass: 'floatRight'
  };
  this.behaviors = this.params_.behaviors || {};

  if (!this.behaviors.direction) {
    this.behaviors.direction = 'up'; // up or down
  }
  if (!this.behaviors.bgColor) {
    this.behaviors.bgColor = '#000000';
  }
  if (!this.behaviors.borderColor) {
    this.behaviors.borderColor = '#9bec1c';
  }
  if (!this.behaviors.radius) {
    this.behaviors.radius = 8;
  }
  if (!this.behaviors.glowPadding) {
    this.behaviors.glowPadding = 20;
  }
  if (!this.behaviors.showDuration) {
    this.behaviors.showDuration = 500;
  }
  if (typeof this.behaviors.animate == 'undefined') {
    this.behaviors.animate = true;
  }
  if (!this.behaviors.easing && jQuery.easing && jQuery.easing.easeOutBounce) {
    this.behaviors.easing = 'easeOutBounce';
  }
};

/**
 * Shows the tooltip and its content.
 * @param {Object} data object with the information to be shown.
 * @param {jQuery.Element} the element the tooltip will shown in relation to.
 * @return true if success.
 */
gtv.jq.Tooltip.prototype.show = function(data, element) {
  var tooltip = this;

  // hide it first
  tooltip.hide();

  // build container and inner structure
  tooltip.container = $('<div></div>').attr('id', tooltip.containerId);
  if (tooltip.styles.containerClass) {
    tooltip.container.addClass(tooltip.styles.containerClass);
  }

  var h2 = $('<h2></h2>').append(data.title);
  var h3 = $('<h3></h3>').append(data.subTitle);
  var leftDesc = $('<span></span>').append(data.descriptionLeft);
  var rightDesc = $('<span></span>').append(data.descriptionRight);
  tooltip.canvasBg = $('<canvas></canvas>').attr('id', 'tooltipBg');

  if (tooltip.styles.titleClass) {
    h2.addClass(tooltip.styles.titleClass);
  }
  if (tooltip.styles.subTitleClass) {
    h3.addClass(tooltip.styles.divClass);
  }
  if (tooltip.styles.leftDescClass) {
    leftDesc.addClass(tooltip.styles.leftDescClass);
  }
  if (tooltip.styles.rightDescClass) {
    rightDesc.addClass(tooltip.styles.rightDescClass);
  }

  tooltip.container.append(h2);
  tooltip.container.append(h3);
  tooltip.container.append(leftDesc);
  tooltip.container.append(rightDesc);
  tooltip.holder.append(tooltip.container);
  tooltip.holder.append(tooltip.canvasBg);
  // build canvas bg, locate it and animate it
  tooltip.buildCanvas(element);
  // hide on timeout
  if (tooltip.behaviors.hideTimeout) {
    tooltip.hideTimeout = setTimeout(function() {
      tooltip.holder.fadeOut(600, function() {
        tooltip.hide();
      });
    }, tooltip.behaviors.hideTimeout);
  }
  return true;
};

/**
 * Builds the canvas component for the tooltip.
 * @param {jQuery.Element} the element the tooltip will shown in relation to.
 */
gtv.jq.Tooltip.prototype.buildCanvas = function(element) {
  var currentWidth = this.container.innerWidth();
  var currentHeight = this.container.innerHeight();

  // calculate tooltip position left
  var pos = element.offset();
  var currentX = pos.left + (element.innerWidth() / 2) - (currentWidth / 2)
      - this.behaviors.glowPadding;

  var diff = 0;
  if (currentX < 0) {
    diff = -currentX + 3;
    currentX = 3;
  } else {
    var zoom = gtv.jq.GtvCore.getZoom();
    var tempDiff = ($(window).width() / zoom) - currentX - currentWidth
        - this.behaviors.glowPadding * 2;
    if (tempDiff < 0) {
      diff = tempDiff - 3;
      currentX = currentX + diff;
    }
  }

  // build canvas bg
  this.canvasBg.attr('width', (currentWidth + this.behaviors.glowPadding*2))
      .attr('height', (currentHeight + this.behaviors.glowPadding*2));

  // build canvas context
  var ctx = document.getElementById('tooltipBg').getContext('2d');

  // give some padding
  // translate shape in order to give margin to the glow to be shown
  ctx.translate(this.behaviors.glowPadding, this.behaviors.glowPadding);

  // begin fill
  ctx.beginPath();
  ctx.lineWidth = 2;
  ctx.fillStyle = this.behaviors.bgColor;
  ctx.strokeStyle = this.behaviors.borderColor;

  // move to top-left corner
  ctx.moveTo(this.behaviors.radius, 0);
  if (this.behaviors.direction == 'up') {
    // draw top side
    ctx.lineTo(currentWidth, 0);
  } else {
    // draw top tip from left to right
    ctx.lineTo(((currentWidth + this.behaviors.radius)/2 - 10 - diff), 0);
    ctx.lineTo((currentWidth + this.behaviors.radius)/2 - diff, -10);
    ctx.lineTo(((currentWidth + this.behaviors.radius)/2 + 10 - diff), 0);
    ctx.lineTo(currentWidth, 0);
  }

  // draw top-right corner
  ctx.quadraticCurveTo((currentWidth + this.behaviors.radius),
                       0,
                       (currentWidth + this.behaviors.radius),
                       this.behaviors.radius);
  // draw right side
  ctx.lineTo((currentWidth + this.behaviors.radius), currentHeight);

  // draw bottom-right corner
  ctx.quadraticCurveTo((currentWidth + this.behaviors.radius),
                       (currentHeight + this.behaviors.radius),
                       currentWidth,
                       (currentHeight + this.behaviors.radius));

  if (this.behaviors.direction == 'up') {
    // draw bottom tip from right to left
    ctx.lineTo(((currentWidth + this.behaviors.radius)/2 + 10 - diff),
               (currentHeight + this.behaviors.radius));
    ctx.lineTo((currentWidth + this.behaviors.radius)/2 - diff,
               (currentHeight + this.behaviors.radius) + 10);
    ctx.lineTo(((currentWidth + this.behaviors.radius)/2 - 10 - diff),
               (currentHeight + this.behaviors.radius));
    ctx.lineTo(this.behaviors.radius, (currentHeight + this.behaviors.radius));
  } else {
    // draw bottom side
    ctx.lineTo(this.behaviors.radius, (currentHeight + this.behaviors.radius));
  }
  // draw bottom-left corner
  ctx.quadraticCurveTo(0, (currentHeight + this.behaviors.radius),
                       0, currentHeight);

  // draw left side
  ctx.lineTo(0, this.behaviors.radius);

  // draw top-left corner
  ctx.quadraticCurveTo(0, 0, this.behaviors.radius, 0);

  ctx.fill();
  ctx.stroke();

  // calculate tooltip position top
  var currentY = null;
  var finalY = null;
  if (this.behaviors.direction == 'up') {
    currentY = element.offset().top - currentHeight
        - this.behaviors.glowPadding*2 + 10;
    finalY = currentY - 15;
  } else if (this.behaviors.direction == 'down') {
    currentY = pos.top + element.innerHeight() - 10;
    finalY = currentY + 15;
  }

  this.holder.css('top', currentY + 'px').css('left', currentX + 'px');
  // animate
  if (this.behaviors.animate) {
    this.holder.stop().animate({
        opacity: '1',
        top: finalY
      },
      this.behaviors.showDuration,
      this.behaviors.easing);
  } else {
    this.holder.css('top', gtv.jq.GtvCore.getInt(finalY)).css('opacity', 1);
  }
};

/**
 * Updates the tooltip visibility state.
 * @param {boolean} true if setting the tooltip as visible.
 */
gtv.jq.Tooltip.prototype.setVisible = function(visible) {
  if (this.holder) {
    this.holder.css('display', (visible?'block':'none'));
  }
};

/**
 * Hides and removes the tooltip from screen.
 * @param {boolean} true if setting the tooltip as visible.
 */
gtv.jq.Tooltip.prototype.hide = function() {
  this.holder.stop();

  if (this.hideTimeout) {
    clearTimeout(this.hideTimeout);
  }

  if (this.container) {
    this.container.remove();
  }

  if (this.canvasBg) {
    this.canvasBg.remove();
  }

  if (this.holder) {
    this.holder.css('display', 'none')
        .css('position', 'absolute')
        .css('top', '0px')
        .css('left', '0px')
        .css('zIndex', '999999999')
        .css('display', 'block')
        .css('opacity', '0');
  }
};
