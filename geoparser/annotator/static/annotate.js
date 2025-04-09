// annotate.js

// Variables to hold map and markers
var map = null;
var markersGroup = null;

// Event handler function references
var toggleView = null;
var searchButtonListener = null;
var queryTextInputListener = null;

// Variables for event handler elements
var searchButton = null;
var queryTextInput = null;

document.addEventListener('DOMContentLoaded', function() {
    // Variables for the current document
    var path = window.location.href.split('?')[0];
    var sessionId = path.split('/').at(-4);
    var docIndex = Number(path.split('/').at(-2));
    var progressBar = document.getElementById('progress-bar-' + docIndex);

    // Get the document text container and load spinner
    var documentText = document.getElementById('document-text');
    var taggingLoadSpinner = document.getElementById('toponym-recognition-indicator');

    // Only run the document-specific annotation code if there's an actual documentText container
    // (i.e., if a document is present).
    var totalTextLength = 0;
    if (documentText) {
        totalTextLength = documentText.textContent.length;
    }

    // Variables for context menu and editing
    var contextMenu = document.getElementById('context-menu');
    var selectedToponym = null;
    var isEditing = false;
    var isDragging = false;
    var dragSide = null;
    var initialX = 0;
    var originalStart = 0;
    var originalEnd = 0;
    var currentToponymElement = null;
    var documents = null;

    var documentList = document.getElementById('document-list');

    var sessionSettings = {};

    // Settings Button
    var settingsBtn = document.getElementById('settings-btn');
    var settingsModalElement = document.getElementById('settingsModal');
    var settingsModal = new bootstrap.Modal(settingsModalElement);
    var settingsForm = document.getElementById('settings-form');
    var oneSensePerDiscourseCheckbox = document.getElementById('one-sense-per-discourse');
    var autoCloseAnnotationModalCheckbox = document.getElementById('auto-close-annotation-modal');

    // Fetch session settings
    fetch(`${urlBase}/session/${sessionId}/settings`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 200) {
            return response.json();
        } else {
            alert('Failed to load settings.');
        }
    })
    .then(data => {
        if (Boolean(data)) {
            sessionSettings = data;
        }
    });

    // Fetch documents in the session
    fetch(`${urlBase}/session/${sessionId}/documents`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 200) {
            return response.json();
        } else {
            alert('Failed to load documents.');
        }
    })
    .then(data => {
        if (Boolean(data)) {
            documents = data;
            markTaggedDocuments(documents);
            prepareCurrentDocument(documents)
            .then(() => {
                tagUntaggedDocuments(documents);
            });
        }
    });

    // Function to mark all documents that have already been tagged
    function markTaggedDocuments(documents) {
        let i = 0;
        while (i < documents.length) {
            let currentDoc = documents[i];
            if (i !== docIndex && currentDoc["spacy_applied"] === true) {
                markDocumentReady(i);
            }
            i++;
        }
    }

    // Function to prepare current document for editing (only if documentText exists)
    function prepareCurrentDocument(documents) {
        if (!documentText) {
            // If there's no document text container, there's nothing to parse or show
            return Promise.resolve(true);
        }

        let i = 0;
        let prom = Promise.resolve(true);
        while (i < documents.length) {
            let currentDoc = documents[i];
            if (i === docIndex) {
                if (currentDoc["spacy_applied"] === false) {
                    taggingLoadSpinner.style.display = "block";
                    prom = fetch(`${urlBase}/session/${sessionId}/document/${i}/parse`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => {
                        if (response.status === 200) {
                            // allow editing document
                            taggingLoadSpinner.style.display = "none";
                            documentText.style.display = "block";
                            markDocumentReady(i);
                            reloadDocumentText();
                        } else {
                            alert('Failed to parse document.');
                        }
                    });
                } else {
                    documentText.style.display = "block";
                    markDocumentReady(i);
                }
                break;
            }
            i++;
        }
        return prom;
    }

    // Function to tag all yet untagged documents
    async function tagUntaggedDocuments(documents) {
        let i = 0;
        while (i < documents.length) {
            let currentDoc = documents[i];
            if (i !== docIndex && currentDoc["spacy_applied"] === false) {
                let response = await fetch(`${urlBase}/session/${sessionId}/document/${i}/parse`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                if (response.status === 200) {
                    markDocumentReady(i);                    
                } else {
                    console.error(`Failed to tag document ${i}`);
                }
            }
            i++;
        }
    }

    // Function to mark a document as ready in the sidebar
    function markDocumentReady(docId) {
        let readyIndicator = document.getElementById(`tagged-${docId}`);
        if (readyIndicator) {
            readyIndicator.style.display = "block";
        }
    }

    // Settings button logic
    settingsBtn.addEventListener('click', function() {
        // Load current settings from the server
        fetch(`${urlBase}/session/${sessionId}/settings`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
        })
        .then(response => {
            if (response.status === 200) {
                return response.json();
            } else {
                alert('Failed to load settings.');
            }
        })
        .then(data => {
            if (Boolean(data)) {
                oneSensePerDiscourseCheckbox.checked = data.one_sense_per_discourse;
                autoCloseAnnotationModalCheckbox.checked = data.auto_close_annotation_modal;
                settingsModal.show();
            }
        });
    });

    settingsForm.addEventListener('submit', function(event) {
        event.preventDefault();
        var oneSensePerDiscourse = oneSensePerDiscourseCheckbox.checked;
        var autoCloseAnnotationModal = autoCloseAnnotationModalCheckbox.checked;

        var settingsData = {
            'one_sense_per_discourse': oneSensePerDiscourse,
            'auto_close_annotation_modal': autoCloseAnnotationModal
        };

        fetch(`${urlBase}/session/${sessionId}/settings`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settingsData)
        })
        .then(response => {
            if (response.status === 200) {
                return response.json();
            } else {
                alert('Failed to save settings.');
            }
        })
        .then(data => {
            if (Boolean(data)) {
                // Update sessionSettings variable
                sessionSettings = settingsData;
                settingsModal.hide();
            }
        });
    });

    // Function to restore scroll position of the document list
    function restoreScrollPosition() {
        var savedScrollPos = sessionStorage.getItem('scrollPos');
        if (savedScrollPos !== null) {
            documentList.scrollTop = parseInt(savedScrollPos, 10);
        }
        // After restoring the scroll position, make the panel visible
        documentList.style.visibility = 'visible';
    }

    // Hide the panel until the scroll is restored
    documentList.style.visibility = 'hidden';

    // Restore the scroll position when the page loads
    restoreScrollPosition();

    // Save the scroll position whenever the user scrolls the Documents panel
    documentList.addEventListener('scroll', function() {
        var scrollPos = documentList.scrollTop;
        sessionStorage.setItem('scrollPos', scrollPos);
    });

    // Only run if document text exists
    if (documentText) {
        // Event delegation for clicks in the document text
        documentText.addEventListener('click', function(event) {
            if (isEditing || isDragging) return;
            var toponym = event.target.closest('.toponym');
            if (toponym) {
                var start = parseInt(toponym.getAttribute('data-start'));
                var end = parseInt(toponym.getAttribute('data-end'));
                var text = toponym.textContent;

                // Store current toponym info for use in modal
                var currentToponym = {
                    start: start,
                    end: end,
                    text: text,
                    element: toponym
                };

                // Show the annotation modal
                showAnnotationModal(currentToponym);
            }
        });

        // Event delegation for right-clicks in the document text
        documentText.addEventListener('contextmenu', function(event) {
            event.preventDefault();
            if (isEditing || isDragging) return;
            var toponym = event.target.closest('.toponym');
            if (toponym) {
                selectedToponym = toponym;
                showContextMenu(event.pageX, event.pageY, true);
            } else {
                // Check if text is selected for creating new annotation
                var selection = window.getSelection();
                var selectedText = selection.toString().trim();
                if (selectedText.length > 0) {
                    var range = selection.getRangeAt(0);
                    var originalText = range.toString();

                    // Trim the selected text to remove leading/trailing whitespace
                    var trimmedText = originalText.trim();

                    // Calculate the difference caused by trimming leading/trailing whitespaces
                    var leadingWhitespaceLength = originalText.length - originalText.trimStart().length;

                    var startOffset = getCharOffset(range.startContainer, range.startOffset) + leadingWhitespaceLength;
                    var endOffset = getCharOffset(range.endContainer, range.endOffset)
                        - (originalText.length - trimmedText.length - leadingWhitespaceLength);

                    selectedToponym = {
                        start: startOffset,
                        end: endOffset,
                        text: trimmedText
                    };

                    showContextMenu(event.pageX, event.pageY, false);
                }
            }
        });

        // Hide context menu when clicking elsewhere
        document.addEventListener('click', function(event) {
            if (!contextMenu.contains(event.target)) {
                contextMenu.style.display = 'none';
            }
        });

        // Context Menu Actions
        document.getElementById('context-create').addEventListener('click', function() {
            contextMenu.style.display = 'none';
            createAnnotation(selectedToponym);
        });

        document.getElementById('context-delete').addEventListener('click', function() {
            contextMenu.style.display = 'none';
            deleteAnnotation(selectedToponym);
        });

        document.getElementById('context-edit').addEventListener('click', function() {
            contextMenu.style.display = 'none';
            editAnnotation(selectedToponym);
        });

        // Show context menu
        function showContextMenu(x, y, hasEditOptions) {
            contextMenu.style.left = x + 'px';
            contextMenu.style.top = y + 'px';
            contextMenu.style.display = 'block';

            document.getElementById('context-create').style.display = hasEditOptions ? 'none' : 'block';
            document.getElementById('context-edit').style.display = hasEditOptions ? 'block' : 'none';
            document.getElementById('context-delete').style.display = hasEditOptions ? 'block' : 'none';
        }

        // Functions to get character offsets considering HTML tags
        function getCharOffset(node, offset) {
            var range = document.createRange();
            range.setStart(documentText, 0);
            range.setEnd(node, offset);
            return range.toString().length;
        }

        // Function to create a new annotation
        function createAnnotation(toponymInfo) {
            fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/annotation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    'start': toponymInfo.start,
                    'end': toponymInfo.end,
                    'text': toponymInfo.text
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Re-render the document text
                    reloadDocumentText();
                } else {
                    alert('Failed to create annotation: ' + data.error);
                }
            });
        }

        // Function to delete an annotation
        function deleteAnnotation(toponymElement) {
            var start = parseInt(toponymElement.getAttribute('data-start'));
            var end = parseInt(toponymElement.getAttribute('data-end'));

            fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/annotation?start=${start}&end=${end}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Re-render the document text
                    reloadDocumentText();
                } else {
                    alert('Failed to delete annotation: ' + data.error);
                }
            });
        }

        // Function to edit an annotation
        function editAnnotation(toponymElement) {
            isEditing = true;
            currentToponymElement = toponymElement;
            var start = parseInt(toponymElement.getAttribute('data-start'));
            var end = parseInt(toponymElement.getAttribute('data-end'));

            originalStart = start;
            originalEnd = end;

            // Add drag handles
            var leftHandle = document.createElement('div');
            leftHandle.classList.add('drag-handle', 'left');
            var rightHandle = document.createElement('div');
            rightHandle.classList.add('drag-handle', 'right');
            toponymElement.appendChild(leftHandle);
            toponymElement.appendChild(rightHandle);

            leftHandle.addEventListener('mousedown', function(event) {
                event.stopPropagation();
                event.preventDefault();
                isDragging = true;
                dragSide = 'left';
                initialX = event.clientX;
                document.addEventListener('mousemove', handleMouseMove);
                document.addEventListener('mouseup', handleMouseUp);
            });

            rightHandle.addEventListener('mousedown', function(event) {
                event.stopPropagation();
                event.preventDefault();
                isDragging = true;
                dragSide = 'right';
                initialX = event.clientX;
                document.addEventListener('mousemove', handleMouseMove);
                document.addEventListener('mouseup', handleMouseUp);
            });
        }

        function handleMouseMove(event) {
            if (isDragging && currentToponymElement) {
                var deltaX = event.clientX - initialX;
                var newStart = originalStart;
                var newEnd = originalEnd;

                // Approximate character width (adjust if necessary)
                var charWidth = 7;

                var charDelta = Math.round(deltaX / charWidth);

                if (dragSide === 'left') {
                    newStart = originalStart + charDelta;
                    if (newStart < 0) newStart = 0;
                    if (newStart >= newEnd) newStart = newEnd - 1;
                } else if (dragSide === 'right') {
                    newEnd = originalEnd + charDelta;
                    if (newEnd > totalTextLength) newEnd = totalTextLength;
                    if (newEnd <= newStart) newEnd = newStart + 1;
                }

                // Continuously update the document text and the annotation as the user drags
                updateToponym(newStart, newEnd);
            }
        }

        function handleMouseUp(event) {
            if (isDragging && currentToponymElement) {
                isDragging = false;
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);

                // Remove drag handles
                var handles = currentToponymElement.querySelectorAll('.drag-handle');
                handles.forEach(function(handle) {
                    handle.remove();
                });

                isEditing = false;

                var newStart = parseInt(currentToponymElement.getAttribute('data-start'));
                var newEnd = parseInt(currentToponymElement.getAttribute('data-end'));
                var newText = currentToponymElement.textContent;

                fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/annotation`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        'old_start': originalStart,
                        'old_end': originalEnd,
                        'new_start': newStart,
                        'new_end': newEnd,
                        'new_text': newText
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Re-render the document text
                        reloadDocumentText();
                    } else {
                        alert('Failed to edit annotation: ' + data.error);
                    }
                });
            }
        }

        function updateToponym(newStart, newEnd) {
            // Extract the text before the annotation, the annotation itself, and the text after
            var beforeToponym = documentText.textContent.substring(0, newStart);
            var updatedToponym = documentText.textContent.substring(newStart, newEnd);
            var afterToponym = documentText.textContent.substring(newEnd);

            // Construct the new document text by inserting the updated annotation
            var updatedContent =
                beforeToponym +
                '<span class="toponym" data-start="' + newStart + '" data-end="' + newEnd + '">' +
                updatedToponym +
                '</span>' +
                afterToponym;

            // Update the full document text by replacing the documentText's innerHTML
            documentText.innerHTML = updatedContent;

            // Update the reference to the current toponym element to the new one
            currentToponymElement = document.querySelector('.toponym[data-start="' + newStart + '"][data-end="' + newEnd + '"]');
        }

        // Function to reload the document text from the server
        function reloadDocumentText() {
            fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/text`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    documentText.innerHTML = data.pre_annotated_text;

                    // Update totalTextLength
                    totalTextLength = documentText.textContent.length;

                    // Update progress bar
                    updateProgressBar();

                } else {
                    alert('Failed to reload document text: ' + data.error);
                }
            });
        }

        // Function to update progress bar
        function updateProgressBar() {
            // Fetch updated progress from the server
            fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/progress`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    var progressPercentage = data.progress_percentage;
                    progressBar.style.width = progressPercentage + '%';
                    progressBar.setAttribute('aria-valuenow', progressPercentage);
                }
            });
        }

        // Show Annotation Modal function
        function showAnnotationModal(currentToponym) {
            var modalElement = document.getElementById('annotationModal');
            var modal = new bootstrap.Modal(modalElement);
            var modalCandidateList = document.getElementById('modal-candidate-list');
            var modalFilterPanel = document.getElementById('modal-filter-panel');
            var modalTitle = modalElement.querySelector('.modal-title');
            var noneOptionDiv = document.getElementById('none-option');

            // Get the elements for toggle buttons, searchButton, queryTextInput
            var listViewBtn = document.getElementById('list-view-btn');
            var mapViewBtn = document.getElementById('map-view-btn');
            var searchButton = document.getElementById('search-button');
            var queryTextInput = document.getElementById('query-text-input');
            var existingCandidateData = null;

            // Set the modal title to the toponym text
            modalTitle.textContent = currentToponym.text;

            // Set the query text input to the toponym text
            queryTextInput.value = currentToponym.text;

            // Variables for map view
            var mapView = true; // Map view is default
            var currentFilters = {};
            var filterInputs = {};
            var allCandidates = [];
            var filteredCandidates = [];
            var globalFilterAttributes = [];
            var existing_loc_id = null;
            var lastQueryText = queryTextInput.value.trim();
            var updatingFilters = false;

            var map = null;
            var markersGroup = null;
            var allMarkers = [];

            // Replace elements to remove old event listeners
            listViewBtn.replaceWith(listViewBtn.cloneNode(true));
            mapViewBtn.replaceWith(mapViewBtn.cloneNode(true));
            searchButton.replaceWith(searchButton.cloneNode(true));
            queryTextInput.replaceWith(queryTextInput.cloneNode(true));
            noneOptionDiv.replaceWith(noneOptionDiv.cloneNode(true));

            // Re-assign the elements after cloning
            listViewBtn = document.getElementById('list-view-btn');
            mapViewBtn = document.getElementById('map-view-btn');
            searchButton = document.getElementById('search-button');
            queryTextInput = document.getElementById('query-text-input');
            noneOptionDiv = document.getElementById('none-option');

            // Function to switch views
            function switchToListView() {
                mapView = false;
                listViewBtn.classList.add('active');
                mapViewBtn.classList.remove('active');
                modalMap.style.display = 'none';
                modalCandidateList.style.display = 'block';
                fetchCandidates(queryTextInput.value.trim());
            }

            function switchToMapView() {
                mapView = true;
                mapViewBtn.classList.add('active');
                listViewBtn.classList.remove('active');
                modalCandidateList.style.display = 'none';
                modalMap.style.display = 'block';
                if (!map) {
                    initializeMap();
                }
                fetchCandidates(queryTextInput.value.trim());
            }

            // Function to handle search button click
            function searchButtonClickHandler() {
                fetchCandidates(queryTextInput.value.trim());
            }

            // Function to handle Enter key in query text
            function queryTextInputKeydownHandler(event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    fetchCandidates(queryTextInput.value.trim());
                }
            }

            // Add event listeners
            listViewBtn.addEventListener('click', switchToListView);
            mapViewBtn.addEventListener('click', switchToMapView);
            searchButton.addEventListener('click', searchButtonClickHandler);
            queryTextInput.addEventListener('keydown', queryTextInputKeydownHandler);

            // Set initial active state
            if (mapView) {
                mapViewBtn.classList.add('active');
                listViewBtn.classList.remove('active');
            } else {
                listViewBtn.classList.add('active');
                mapViewBtn.classList.remove('active');
            }

            // Add event listener to the 'None' option
            noneOptionDiv.addEventListener('click', function() {
                saveAnnotation(null);
            });

            // Function to update the 'None' option appearance
            function updateNoneOption() {
                noneOptionDiv.innerHTML = 'No suitable location';

                if (existing_loc_id === null) {
                    noneOptionDiv.classList.add('active', 'bg-primary', 'text-white');

                    // Add deselect button (icon)
                    var deselectBtn = document.createElement('span');
                    deselectBtn.classList.add('deselect-btn', 'ms-2');
                    deselectBtn.innerHTML = '<i class="bi bi-x-circle-fill"></i>';

                    deselectBtn.addEventListener('click', function(event) {
                        event.stopPropagation();
                        deselectCandidate();
                    });

                    noneOptionDiv.appendChild(deselectBtn);
                } else {
                    noneOptionDiv.classList.remove('active', 'bg-primary', 'text-white');
                }
            }

            // Initialize map if in map view
            var modalMap = document.getElementById('modal-map');
            if (mapView) {
                modalCandidateList.style.display = 'none';
                modalMap.style.display = 'block';
                if (!map) {
                    initializeMap();
                }
            } else {
                modalMap.style.display = 'none';
                modalCandidateList.style.display = 'block';
            }

            // Show the modal
            modal.show();

            // Ensure map resizes properly when modal is shown
            modalElement.addEventListener('shown.bs.modal', function () {
                if (mapView && map) {
                    map.invalidateSize();
                    adjustMapView();
                }
            }, { once: true });

            // Clean up when modal is hidden
            modalElement.addEventListener('hidden.bs.modal', function () {
                // Reset filters
                currentFilters = {};
                filterInputs = {};

                // Clean up the map if it exists
                if (map) {
                    map.remove();
                    map = null;
                    markersGroup = null;
                    allMarkers = [];
                }
            }, { once: true });

            // Fetch initial candidates
            fetchCandidates(queryTextInput.value.trim());

            function initializeMap() {
                if (!map) {
                    map = L.map('modal-map').setView([0, 0], 2);
                    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
                        maxZoom: 20
                    }).addTo(map);
                    markersGroup = L.featureGroup().addTo(map);
                }
            }

            // Function to fetch candidates based on query text
            function fetchCandidates(queryText) {
                // Reset filters only if the query text has changed
                if (lastQueryText !== queryText) {
                    currentFilters = {}; // Reset filters
                    lastQueryText = queryText; 
                }

                fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/get_candidates`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        'start': currentToponym.start,
                        'end': currentToponym.end,
                        'text': currentToponym.text,
                        'query_text': queryText
                    })
                })
                .then(response => response.json())
                .then(data => {
                    existingCandidateData = data.existing_candidate;
                    populateCandidates(data.candidates, data.filter_attributes, data.existing_loc_id);
                    existing_loc_id = data.existing_loc_id;
                    updateNoneOption();
                });
            }

            // Function to populate candidates and filters
            function populateCandidates(candidates, filterAttributes, existing_loc_id_param) {
                // Store candidates and existing_loc_id
                allCandidates = candidates;
                existing_loc_id = existing_loc_id_param;

                // Initialize filteredCandidates
                filteredCandidates = allCandidates.slice(); // copy

                // Store filterAttributes globally so buildFilters can access
                globalFilterAttributes = filterAttributes;

                // Build filters
                buildFilters();

                // Apply filters and render candidates
                applyFilters();
            }

            function buildFilters() {
                modalFilterPanel.innerHTML = '';
                filterInputs = {};

                // Create filters
                globalFilterAttributes.forEach(function(attribute) {
                    var label = document.createElement('label');
                    label.textContent = 'Filter by ' + attribute;
                    label.classList.add('form-label');

                    // Collect attribute values from the filteredCandidates
                    var attributeValues = new Set();
                    filteredCandidates.forEach(function(candidate) {
                        var attributes = candidate.attributes;
                        if (attributes[attribute]) {
                            attributeValues.add(attributes[attribute]);
                        }
                    });

                    if (currentFilters[attribute]) {
                        // Filter has a selected value
                        var filterDiv = document.createElement('div');
                        filterDiv.classList.add('input-group', 'mb-3');

                        var input = document.createElement('input');
                        input.type = 'text';
                        input.value = currentFilters[attribute];
                        input.classList.add('form-control');
                        input.readOnly = true;

                        var button = document.createElement('button');
                        button.classList.add('btn', 'btn-outline-secondary');
                        button.type = 'button';
                        button.innerHTML = '<i class="bi bi-x-circle-fill"></i>';

                        button.addEventListener('click', function() {
                            currentFilters[attribute] = '';
                            applyFilters();
                        });

                        filterDiv.appendChild(input);
                        filterDiv.appendChild(button);

                        modalFilterPanel.appendChild(label);
                        modalFilterPanel.appendChild(filterDiv);
                    } else {
                        // No filter selected, show select element
                        var select = document.createElement('select');
                        select.dataset.attribute = attribute;
                        select.classList.add('form-select', 'mb-3');

                        // Add an empty option
                        var emptyOption = document.createElement('option');
                        emptyOption.value = '';
                        emptyOption.textContent = 'All';
                        select.appendChild(emptyOption);

                        // Add options from attributeValues
                        Array.from(attributeValues).sort().forEach(function(value) {
                            var option = document.createElement('option');
                            option.value = value;
                            option.textContent = value;
                            select.appendChild(option);
                        });

                        // Set the select value to the current filter if any
                        select.value = '';

                        modalFilterPanel.appendChild(label);
                        modalFilterPanel.appendChild(select);
                        filterInputs[attribute] = select;

                        // Event listener for the select
                        select.addEventListener('change', function() {
                            var selectedValue = select.value;
                            currentFilters[attribute] = selectedValue;
                            applyFilters();
                        });
                    }
                });
            }

            function applyFilters() {
                updatingFilters = true;

                // Filter the candidates
                filteredCandidates = [];
                allCandidates.forEach(function(candidate) {
                    var attributes = candidate.attributes;
                    var showCandidate = true;
                    Object.keys(currentFilters).forEach(function(attribute) {
                        var filterValue = currentFilters[attribute];
                        var attributeValue = attributes[attribute] ? attributes[attribute].toString() : '';
                        if (filterValue && attributeValue !== filterValue) {
                            showCandidate = false;
                        }
                    });
                    if (showCandidate) {
                        filteredCandidates.push(candidate);
                    }
                });

                // Build filters based on new filteredCandidates
                buildFilters();

                updatingFilters = false;

                // Now display the filtered candidates
                if (mapView) {
                    // Map View
                    if (markersGroup) {
                        markersGroup.clearLayers();
                    }
                    allMarkers = [];

                    var selectedMarker = null;

                    filteredCandidates.forEach(function(candidate) {
                        var lat = candidate.latitude;
                        var lon = candidate.longitude;
                        if (lat !== null && lon !== null) {
                            var markerOptions = {
                                radius: 8,
                                fillColor: '#ffc107',
                                color: '#000',
                                weight: 1,
                                opacity: 1,
                                fillOpacity: 0.8
                            };

                            var loc_id = candidate.loc_id;
                            var isSelected = (existing_loc_id !== null && existing_loc_id !== '') && loc_id == existing_loc_id;

                            if (isSelected) {
                                markerOptions.fillColor = '#0d6efd';
                            }

                            var marker = L.circleMarker([lat, lon], markerOptions);
                            marker.bindPopup(candidate.description);

                            marker.on('mouseover', function(e) {
                                this.openPopup();
                            });
                            marker.on('mouseout', function(e) {
                                this.closePopup();
                            });

                            marker.on('click', function(e) {
                                L.DomEvent.stopPropagation(e);
                                if (isSelected) {
                                    deselectCandidate();
                                } else {
                                    saveAnnotation(loc_id);
                                }
                            });

                            if (isSelected) {
                                selectedMarker = marker;
                            } else {
                                markersGroup.addLayer(marker);
                            }

                            allMarkers.push(marker);
                        }
                    });

                    if (selectedMarker) {
                        markersGroup.addLayer(selectedMarker);
                        selectedMarker.bringToFront();
                    }

                    adjustMapView();

                } else {
                    // List View
                    modalCandidateList.innerHTML = '';

                    var selectedCandidateDiv = null;

                    filteredCandidates.forEach(function(candidate) {
                        var candidateDiv = document.createElement('div');
                        candidateDiv.classList.add('candidate', 'p-2', 'border', 'mb-2');
                        candidateDiv.innerHTML = candidate.description;
                        candidateDiv.dataset.locId = candidate.loc_id;
                        candidateDiv.dataset.attributes = JSON.stringify(candidate.attributes);

                        if (existing_loc_id !== null && candidate.loc_id == existing_loc_id) {
                            candidateDiv.classList.add('bg-primary', 'text-white');

                            var deselectBtn = document.createElement('span');
                            deselectBtn.classList.add('deselect-btn', 'ms-2');
                            deselectBtn.innerHTML = '<i class="bi bi-x-circle-fill"></i>';

                            deselectBtn.addEventListener('click', function(event) {
                                event.stopPropagation();
                                deselectCandidate();
                            });

                            candidateDiv.appendChild(deselectBtn);

                            selectedCandidateDiv = candidateDiv;
                        }

                        candidateDiv.addEventListener('click', function() {
                            saveAnnotation(candidateDiv.dataset.locId);
                        });
                        modalCandidateList.appendChild(candidateDiv);
                    });

                    if (existing_loc_id !== null && selectedCandidateDiv === null) {
                        if (existingCandidateData) {
                            var existingCandidate = existingCandidateData;

                            var candidateDiv = document.createElement('div');
                            candidateDiv.classList.add('candidate', 'p-2', 'border', 'mb-2');
                            candidateDiv.innerHTML = existingCandidate.description;
                            candidateDiv.dataset.locId = existingCandidate.loc_id;
                            candidateDiv.dataset.attributes = JSON.stringify(existingCandidate.attributes);

                            candidateDiv.classList.add('bg-primary', 'text-white');

                            var deselectBtn = document.createElement('span');
                            deselectBtn.classList.add('deselect-btn', 'ms-2');
                            deselectBtn.innerHTML = '<i class="bi bi-x-circle-fill"></i>';

                            deselectBtn.addEventListener('click', function(event) {
                                event.stopPropagation();
                                deselectCandidate();
                            });

                            candidateDiv.appendChild(deselectBtn);
                            selectedCandidateDiv = candidateDiv;
                            modalCandidateList.appendChild(candidateDiv);
                        } else {
                            console.error('Existing candidate data not available');
                        }
                    }

                    if (selectedCandidateDiv) {
                        selectedCandidateDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }

            function adjustMapView() {
                map.whenReady(function() {
                    if (markersGroup && markersGroup.getLayers().length > 0) {
                        var bounds = markersGroup.getBounds();
                        if (bounds.isValid()) {
                            if (markersGroup.getLayers().length === 1) {
                                var latLng = bounds.getCenter();
                                map.setView(latLng, 10);
                            } else {
                                map.fitBounds(bounds, { padding: [50, 50] });
                            }
                        } else {
                            map.setView([0, 0], 2);
                        }
                    } else {
                        map.setView([0, 0], 2);
                    }
                });
            }

            // Function to save the annotation
            function saveAnnotation(loc_id) {
                fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/annotation`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        'text': currentToponym.text,
                        'start': currentToponym.start,
                        'end': currentToponym.end,
                        'loc_id': loc_id
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Update progress bar
                        updateProgressBar();

                        // Re-render the document text
                        reloadDocumentText();

                        // Close the modal based on setting
                        if (sessionSettings.auto_close_annotation_modal) {
                            modal.hide();
                        } else {
                            fetchCandidates(queryTextInput.value.trim());
                        }
                    } else {
                        alert('Failed to save annotation: ' + data.error);
                    }
                });
            }

            // Function to deselect the annotation (reset to unprocessed)
            function deselectCandidate() {
                fetch(`${urlBase}/session/${sessionId}/document/${docIndex}/annotation`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        'text': currentToponym.text,
                        'start': currentToponym.start,
                        'end': currentToponym.end,
                        'loc_id': ''  // reset loc_id to empty
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        updateProgressBar();
                        reloadDocumentText();
                        if (sessionSettings.auto_close_annotation_modal) {
                            modal.hide();
                        } else {
                            fetchCandidates(queryTextInput.value.trim());
                        }
                    } else {
                        alert('Failed to deselect candidate: ' + data.error);
                    }
                });
            }
        }
    }

    // Add Document Button
    var addDocumentBtn = document.getElementById('add-document-btn');
    var addDocumentModal = new bootstrap.Modal(document.getElementById('addDocumentModal'));
    var addDocumentForm = document.getElementById('add-document-form');

    addDocumentBtn.addEventListener('click', function() {
        addDocumentModal.show();
    });

    addDocumentForm.addEventListener('submit', function(event) {
        event.preventDefault();
        var formData = new FormData(addDocumentForm);

        fetch(`${urlBase}/session/${sessionId}/documents`, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.status !== 200) {
                alert('Failed to add documents.');
            } else {
                return response.json();
            }
        })
        .then(data => {
            if (Boolean(data)) {
                // Reload the page to reflect new documents
                window.location.reload();
            }
        });
    });

    // Remove Document Buttons
    var removeDocumentBtns = document.querySelectorAll('.remove-document-btn');
    removeDocumentBtns.forEach(function(btn) {
        btn.addEventListener('click', function(event) {
            var docIndexToRemove = btn.getAttribute('data-doc-index');
            if (confirm('Are you sure you want to remove this document? All annotations for this document will be lost.')) {
                fetch(`${urlBase}/session/${sessionId}/document/${docIndexToRemove}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Reload the page to reflect document removal
                        if (parseInt(docIndexToRemove) === docIndex) {
                            window.location.href = `${urlBase}/session/${sessionId}/document/0/annotate`;
                        } else {
                            window.location.reload();
                        }
                    } else {
                        alert('Failed to remove document.');
                    }
                });
            }
        });
    });
});
