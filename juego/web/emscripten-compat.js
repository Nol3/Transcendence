/**
 * Emscripten compatibility shim for cross-browser support.
 * Load this BEFORE index.js to provide missing Emscripten runtime functions.
 */
(function() {
  'use strict';

  // Ensure Module exists
  if (typeof Module === 'undefined') {
    window.Module = {};
  }

  // Ensure LibraryManager exists with library object
  if (typeof LibraryManager === 'undefined') {
    window.LibraryManager = { library: {} };
  }

  // Define mergeInto if missing
  if (typeof mergeInto === 'undefined') {
    window.mergeInto = function(target, lib) {
      if (!target || typeof target !== 'object') return;
      for (var key in lib) {
        if (lib.hasOwnProperty(key)) {
          target[key] = lib[key];
        }
      }
    };
  }

  // Define UTF8ToString if missing (newer Emscripten)
  if (typeof UTF8ToString === 'undefined') {
    window.UTF8ToString = function(ptr, maxLength) {
      if (!ptr) return '';
      if (!Module.HEAPU8) return '';
      var i = 0;
      var str = '';
      var view = new Uint8Array(Module.HEAPU8.buffer, ptr, maxLength || 4096);
      while (view[i] !== 0 && (!maxLength || i < maxLength)) {
        str += String.fromCharCode(view[i]);
        i++;
      }
      return str;
    };
  }

  // Define Pointer_stringify for older Emscripten compatibility
  if (typeof Pointer_stringify === 'undefined') {
    window.Pointer_stringify = function(ptr, maxLength) {
      if (typeof UTF8ToString !== 'undefined') {
        return UTF8ToString(ptr, maxLength);
      }
      return '';
    };
  }

  // Ensure LibraryManager.library functions are available
  LibraryManager.library.Pointer_stringify = Pointer_stringify;

  console.log('[Emscripten Compat] LibraryManager and utilities available');
})();
