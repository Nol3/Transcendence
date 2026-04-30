/**
 * Module loader wrapper that ensures Emscripten compatibility
 * before the compiled module is loaded.
 */

(function() {
  'use strict';

  // Step 1: Set up global environment
  window.LibraryManager = window.LibraryManager || { library: {} };

  // Step 2: Define mergeInto globally
  window.mergeInto = function(lib, funcs) {
    if (!lib || typeof lib !== 'object') return;
    Object.keys(funcs).forEach(function(key) {
      lib[key] = funcs[key];
    });
  };

  // Step 3: Setup Module
  window.Module = window.Module || {};

  // Step 4: Store original Module properties
  var canvasEl = document.getElementById('canvas');
  if (canvasEl && !window.Module.canvas) {
    window.Module.canvas = canvasEl;
  }

  if (!window.Module.onRuntimeInitialized) {
    window.Module.onRuntimeInitialized = function() {
      var loading = document.getElementById('loading');
      if (loading) {
        loading.classList.add('hidden');
      }
      console.log('[Module Loader] Runtime initialized');
    };
  }

  // Step 5: Patch Module when it's ready
  var originalInit = window.Module.onRuntimeInitialized;
  window.Module.onRuntimeInitialized = function() {
    // Ensure PokerRace functions are available if Module is used for them
    if (typeof originalInit === 'function') {
      originalInit.call(this);
    }

    // Verify critical functions exist
    if (typeof Pointer_stringify !== 'undefined') {
      LibraryManager.library.Pointer_stringify = Pointer_stringify;
    }

    console.log('[Module Loader] Post-init setup complete');
  };

  console.log('[Module Loader] Initialized, waiting for index.js...');
})();
