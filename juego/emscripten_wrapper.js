/**
 * Emscripten LibraryManager wrapper for cross-browser compatibility.
 * Provides the mergeInto function and LibraryManager object that Emscripten
 * post-js files expect, even in browsers where they're not automatically available.
 */

(function() {
    'use strict';

    // Create global Module if it doesn't exist
    if (typeof Module === 'undefined') {
        globalThis.Module = {};
    }

    // Create LibraryManager object if it doesn't exist
    if (typeof LibraryManager === 'undefined') {
        globalThis.LibraryManager = {
            library: {}
        };
    }

    // Define mergeInto function if it doesn't exist
    // This function merges exported functions into the Emscripten library
    if (typeof mergeInto === 'undefined') {
        globalThis.mergeInto = function(targetLibrary, newFunctions) {
            if (!targetLibrary || typeof targetLibrary !== 'object') {
                return;
            }

            for (var key in newFunctions) {
                if (newFunctions.hasOwnProperty(key)) {
                    targetLibrary[key] = newFunctions[key];
                }
            }
        };
    }

    // Define Pointer_stringify if it doesn't exist
    // This function converts WASM memory pointers to strings
    if (typeof Pointer_stringify === 'undefined') {
        globalThis.Pointer_stringify = function(ptr, maxLength) {
            if (!ptr) return '';

            // Try to use UTF8ToString if available (newer Emscripten)
            if (typeof UTF8ToString !== 'undefined') {
                return UTF8ToString(ptr, maxLength);
            }

            // Fallback for older Emscripten or custom implementations
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

    // Define Pointer_stringify in LibraryManager for C code
    if (!LibraryManager.library.Pointer_stringify) {
        LibraryManager.library.Pointer_stringify = globalThis.Pointer_stringify;
    }
})();
