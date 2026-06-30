(function() {
    'use strict';

    function run($) {
        $(document).ready(function() {
            var $form = $('form#sermon_form, form[enctype="multipart/form-data"]');
            if (!$form.length) {
                $form = $('form');
            }

            $form.on('submit', function() {
                document.body.style.cursor = 'wait';
                $('input[type="submit"], button[type="submit"]').prop('disabled', true);
            });
        });
    }

    function tryInit() {
        if (typeof django !== 'undefined' && django.jQuery) {
            run(django.jQuery);
        } else if (typeof jQuery !== 'undefined') {
            run(jQuery);
        } else {
            setTimeout(tryInit, 50);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tryInit);
    } else {
        tryInit();
    }
})();
