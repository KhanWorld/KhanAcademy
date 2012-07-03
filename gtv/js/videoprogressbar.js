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
 * @fileoverview Classes for Video Progress Bar Control
 *
 * 
 */

var gtv = gtv || {
  jq: {}
};

/**
 * VideoProgressBarParams class holds configuration values specific to VideoProgressBar.
 * @constructor
 */
gtv.jq.VideoProgressBarParams = function() {
};

/**
 * CreateParams for the VideoProgressBar control.
 * @type {CreateParams}
 */
gtv.jq.VideoProgressBarParams.prototype.createParams = null;

/**
 * Behaviors for the VideoProgressBar control.
 * @type {VideoProgressBarBehaviors}
 */
gtv.jq.VideoControlParams.prototype.behaviors = null;

/**
 * VideoProgressBarBehaviors configures the behaviors for a VideoProgressBar control.
 * @constructor
 */
gtv.jq.VideoProgressBarBehaviors = function() {
};

/**
 * VideoProgressBar class. VideoProgressBar control shows the
 * duration and elapsed time of a video.
 * Also shows a progress bar with both: loaded time and elapsed time.
 * @constructor
 */
gtv.jq.VideoProgressBar = function() {
  this.intLoadedTime = 0;
  this.intElapsedTime = 0;
  this.intDuration = 0;
}

/**
 * Removes the control from its container and from the key controller.
 */
gtv.jq.VideoProgressBar.prototype.deleteControl = function() {
  if (this.container) {
    this.container.remove();
    this.container = null;
  }
};

/**
 * Creates the VideoProgressBar inner components.
 * @param {gtv.jq.VideoProgressBarParams} videoProgressBarParms
 * @return {boolean} true on success
 */
gtv.jq.VideoProgressBar.prototype.makeControl = function(videoProgressBarParms)
{
  this.params_ = jQuery.extend(videoProgressBarParms.createParams, videoProgressBarParms);

  if (!this.params_.containerId) {
    return false;
  }

  this.holder = this.params_.topParent;
  this.containerId = this.params_.containerId;
  this.styles = this.params_.styles || {};
  this.behaviors = this.params_.behaviors || {};
  this.callbacks = this.params_.callbacks || {};

  var progressBar = this;

  progressBar.container =
      $('<div></div>').attr('id', progressBar.containerId)
          .addClass('progressbar-control ' + progressBar.styles.container);
  progressBar.elapsedTime = $('<div></div>')
      .addClass('progress-elapsed-time ' + progressBar.styles.elapsedTime)
      .html('00:00');
  progressBar.progressBack = $('<div></div>')
      .addClass('progress-bar-back ' + progressBar.styles.progressBack);
  progressBar.playPogress = $('<div></div>')
      .css('width', '0px')
      .addClass('progress-play-progress ' + progressBar.styles.playProgress);
  progressBar.loadPogress = $('<div></div>')
      .css('width', '0px')
      .addClass('progress-load-progress ' + progressBar.styles.loadProgress);
  progressBar.duration = $('<div></div>')
      .addClass('progress-duration ' + progressBar.styles.duration)
      .html('00:00');

  progressBar.progressBack.bind('mousemove', function(e) {
    if (progressBar.intDuration > 0) {
      var backWidth = progressBar.progressBack.width();
      var backOffset = progressBar.progressBack.offset();

      if (!progressBar.timeTooltip) {
        progressBar.timeTooltip = $('<div></div>').css('position', 'absolute')
            .css('display', 'none')
            .css('zIndex', '10010')
            .addClass('progress-tooltip ' + progressBar.styles.tooltip);
        $(document.body).append(progressBar.timeTooltip);
      }

      var zoom = gtv.jq.GtvCore.getZoom();

      progressBar.timeTooltip.html(progressBar.formatSeconds(
          progressBar.intDuration *
              (e.clientX/zoom - backOffset.left) / backWidth));

      var tooltipWidth = progressBar.timeTooltip.width();
      var tooltipHeight = progressBar.timeTooltip.height();

      var tooltipTop = e.clientY/zoom - e.offsetY/zoom - tooltipHeight;
      var tooltipLeft = e.clientX/zoom - (tooltipWidth / 2);

      progressBar.timeTooltip.css('top', tooltipTop)
          .css('left', tooltipLeft)
          .css('display', '');
    }
  });

  progressBar.progressBack.bind('mouseleave', function(e) {
    progressBar.hideTimeTooltip();
  });

  progressBar.progressBack.bind('click', function(e) {
    if (typeof progressBar.callbacks.onTimeSelected == 'function') {
      var zoom = gtv.jq.GtvCore.getZoom();

      var backWidth = progressBar.progressBack.width();
      var backOffset = progressBar.progressBack.offset();

      var seconds = progressBar.intDuration *
          (e.clientX/zoom - backOffset.left) / backWidth;

      progressBar.callbacks.onTimeSelected(seconds);
    }
  });

  progressBar.progressBack
      .append(progressBar.playPogress)
      .append(progressBar.loadPogress);
  progressBar.container.append(progressBar.elapsedTime)
      .append(progressBar.progressBack)
      .append(progressBar.duration);

  progressBar.holder.append(progressBar.container);

  return true;
};

/**
 * Formats a number of seconds into a string.
 * @param {number} seconds to be formatted.
 * @return {string} time as a formatted string.
 */
gtv.jq.VideoProgressBar.prototype.formatSeconds = function(seconds) {
  return gtv.jq.GtvCore.formatTime(
      seconds,
      (seconds >= 3600) ? 'hours' : 'minutes');
};

/**
 * Updates the loaded time in seconds.
 * @param {number} seconds.
 */
gtv.jq.VideoProgressBar.prototype.setLoadedTime = function(seconds) {
  if (this.container) {
    this.intLoadedTime = seconds;
    this.updateProgress();
  }
};

/**
 * Updates the elapsed time in seconds.
 * @param {number} seconds.
 */
gtv.jq.VideoProgressBar.prototype.setElapsedTime = function(seconds) {
  if (this.container) {
    this.intElapsedTime = seconds;
    this.elapsedTime.html(this.formatSeconds(seconds));
    this.updateProgress();
  }
};

/**
 * Sets the total duration in seconds.
 * @param {number} seconds.
 */
gtv.jq.VideoProgressBar.prototype.setDuration = function(seconds) {
  if (this.container) {
    this.intDuration = seconds;
    this.duration.html(this.formatSeconds(seconds));
    this.updateProgress();
  }
};

/**
 * Refreshes the loaded and progress bars.
 */
gtv.jq.VideoProgressBar.prototype.updateProgress = function() {
  if (this.container) {
    var loaded = Math.round(this.intLoadedTime * 100 / this.intDuration);
    var progress = Math.round(this.intElapsedTime * 100 / this.intDuration);

    if (loaded >= progress) {
      this.loadPogress.css('width', (loaded - progress) + '%');
    } else {
      this.loadPogress.css('width', '0px');
    }
    this.playPogress.css('width', progress + '%');
  }
};

/**
 * Resets the loaded and progress bars and the elapsed time.
 */
gtv.jq.VideoProgressBar.prototype.resetElapsedTime = function() {
  if (this.container) {
    this.setElapsedTime(0);
    this.playPogress.css('width', '0px');
    this.loadPogress.css('width', '0px');
  }
};

/**
 * Resets the loaded and progress bars, the elapsed time and duration.
 */
gtv.jq.VideoProgressBar.prototype.resetAll = function() {
  if (this.container) {
    this.resetElapsedTime();
    this.setDuration(0);
  }
};

/**
 * Hides the seeking tooltip.
 */
gtv.jq.VideoProgressBar.prototype.hideTimeTooltip = function() {
  if (this.timeTooltip) {
    this.timeTooltip.css('display', 'none');
  }
};
