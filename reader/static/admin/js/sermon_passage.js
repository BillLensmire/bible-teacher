(function() {
    'use strict';

    var $ = null;
    var BOOK_SELECT = 'select[id$="-book"]';
    var CHAPTER_SELECT = 'select[id$="-chapter"]';
    var VERSE_START_SELECT = 'select[id$="-verse_start"]';
    var VERSE_END_SELECT = 'select[id$="-verse_end"]';

    function getPrefixFromId(id) {
        var match = id.match(/^id_(.+)-(?:book|chapter|verse_start|verse_end)$/);
        return match ? match[1] : null;
    }

    function populateSelect($select, options, selectedValue) {
        var currentVal = String($select.val() || '');
        $select.empty();
        $select.append($('<option>', {value: '', text: '---------'}));
        options.forEach(function(opt) {
            var val = String(opt);
            $select.append($('<option>', {value: val, text: val}));
        });
        if (selectedValue !== undefined && selectedValue !== null && selectedValue !== '') {
            $select.val(String(selectedValue));
        } else if (currentVal && options.some(function(o) { return String(o) === currentVal; })) {
            $select.val(currentVal);
        }
    }

    function loadChapters($bookSelect, selectedChapter) {
        var book = $bookSelect.val();
        var prefix = getPrefixFromId($bookSelect.attr('id'));
        if (!book || !prefix) return;

        var $chapterSelect = $('#id_' + prefix + '-chapter');
        var $verseStartSelect = $('#id_' + prefix + '-verse_start');
        var $verseEndSelect = $('#id_' + prefix + '-verse_end');

        $chapterSelect.prop('disabled', true);
        $verseStartSelect.prop('disabled', true);
        $verseEndSelect.prop('disabled', true);

        $.getJSON('/api/book-chapters/' + encodeURIComponent(book) + '/')
            .done(function(data) {
                populateSelect($chapterSelect, data.chapters, selectedChapter);
                $chapterSelect.prop('disabled', false);
                if (selectedChapter === undefined) {
                    $verseStartSelect.empty().append($('<option>', {value: '', text: '---------'}));
                    $verseEndSelect.empty().append($('<option>', {value: '', text: '---------'}));
                    $verseStartSelect.prop('disabled', false);
                    $verseEndSelect.prop('disabled', false);
                } else {
                    var vsStart = $verseStartSelect.data('initial-value');
                    var vsEnd = $verseEndSelect.data('initial-value');
                    loadVerses($chapterSelect, vsStart, vsEnd);
                }
            })
            .fail(function() {
                $chapterSelect.prop('disabled', false);
                $verseStartSelect.prop('disabled', false);
                $verseEndSelect.prop('disabled', false);
            });
    }

    function loadVerses($chapterSelect, selectedVerseStart, selectedVerseEnd) {
        var chapter = $chapterSelect.val();
        var prefix = getPrefixFromId($chapterSelect.attr('id'));
        if (!chapter || !prefix) return;

        var book = $('#id_' + prefix + '-book').val();
        if (!book) return;

        var $verseStartSelect = $('#id_' + prefix + '-verse_start');
        var $verseEndSelect = $('#id_' + prefix + '-verse_end');

        $verseStartSelect.prop('disabled', true);
        $verseEndSelect.prop('disabled', true);

        $.getJSON('/api/chapter-verses/' + encodeURIComponent(book) + '/' + chapter + '/')
            .done(function(data) {
                populateSelect($verseStartSelect, data.verses, selectedVerseStart);
                populateSelect($verseEndSelect, data.verses, selectedVerseEnd);
                $verseStartSelect.prop('disabled', false);
                $verseEndSelect.prop('disabled', false);
            })
            .fail(function() {
                $verseStartSelect.prop('disabled', false);
                $verseEndSelect.prop('disabled', false);
            });
    }

    function initRow($row) {
        var $bookSelect = $row.find(BOOK_SELECT);
        var $chapterSelect = $row.find(CHAPTER_SELECT);
        var $verseStartSelect = $row.find(VERSE_START_SELECT);
        var $verseEndSelect = $row.find(VERSE_END_SELECT);

        $verseStartSelect.data('initial-value', $verseStartSelect.val());
        $verseEndSelect.data('initial-value', $verseEndSelect.val());

        if ($bookSelect.val()) {
            var chapterVal = $chapterSelect.val();
            if (chapterVal) {
                loadChapters($bookSelect, chapterVal);
            }
        }
    }

    function run(jq) {
        $ = jq;
        $(document).ready(function() {
            $('.inline-related').each(function() {
                initRow($(this));
            });

            $(document).on('change', BOOK_SELECT, function() {
                var $bookSelect = $(this);
                var prefix = getPrefixFromId($bookSelect.attr('id'));
                if (!prefix) return;
                var $chapterSelect = $('#id_' + prefix + '-chapter');
                var $verseStartSelect = $('#id_' + prefix + '-verse_start');
                var $verseEndSelect = $('#id_' + prefix + '-verse_end');
                $chapterSelect.val('').trigger('change');
                $verseStartSelect.empty().append($('<option>', {value: '', text: '---------'}));
                $verseEndSelect.empty().append($('<option>', {value: '', text: '---------'}));
                loadChapters($bookSelect);
            });

            $(document).on('change', CHAPTER_SELECT, function() {
                var $chapterSelect = $(this);
                var prefix = getPrefixFromId($chapterSelect.attr('id'));
                if (!prefix) return;
                var $verseStartSelect = $('#id_' + prefix + '-verse_start');
                var $verseEndSelect = $('#id_' + prefix + '-verse_end');
                $verseStartSelect.empty().append($('<option>', {value: '', text: '---------'}));
                $verseEndSelect.empty().append($('<option>', {value: '', text: '---------'}));
                loadVerses($chapterSelect);
            });

            $(document).on('formset:added', function(event, $row, formsetName) {
                if (formsetName === 'sermonpassage_set') {
                    initRow($row);
                }
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
