"use strict";

(function () {
    /** Logic for correctly extending a class in ES5 */
    function extendClass(superClass) {
        const _constructor = function () {
            Object.getPrototypeOf(_constructor).apply(this, arguments);
        }

        _constructor.prototype = Object.create(superClass.prototype, {
            constructor: {
                value: _constructor,
                writable: true,
                configurable: true
            }
        });
        Object.setPrototypeOf(_constructor, superClass);

        return _constructor;
    }

    Object.extendClass = extendClass;
})();
