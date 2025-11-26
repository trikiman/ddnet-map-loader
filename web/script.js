document.addEventListener('DOMContentLoaded', () => {
    // ===== Theme Toggle =====
    const themeToggle = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('theme') || 'light';
    
    // Apply saved theme on load
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        if (themeToggle) themeToggle.textContent = '☀️';
    }
    
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === 'dark') {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                themeToggle.textContent = '🌙';
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeToggle.textContent = '☀️';
            }
        });
    }

    const dropZone = document.getElementById('dropZone');
    const progressContainer = document.querySelector('.progress-container');
    const progressBar = document.querySelector('.progress');
    const progressLabel = document.querySelector('.progress-label');
    const mapsList = document.querySelector('.maps-list');

    // Format file size helper
    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('drag-over');
    }

    function unhighlight(e) {
        dropZone.classList.remove('drag-over');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.name.endsWith('.map')) {
                uploadFile(file);
            } else {
                alert('Please upload only .map files');
            }
        }
    }

    // Function to start auto-update watcher after upload
    async function startAutoUpdateWatcher(filePath, originalName) {
        const baseUrl = window.location.origin;
        const autoUpdateStatus = document.getElementById('autoUpdateStatus');
        
        if (!autoUpdateStatus) return;
        
        autoUpdateStatus.style.display = 'block';
        autoUpdateStatus.style.background = '#3d2e0a';
        autoUpdateStatus.style.border = '1px solid #ff9800';
        autoUpdateStatus.innerHTML = '⏳ Starting auto-update watcher...';
        
        try {
            const response = await fetch(`${baseUrl}/start-auto-update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filePath: filePath,
                    serverUrl: baseUrl
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Use original filename for cleaner display
                const displayName = originalName || filePath.split('\\').pop().split('/').pop();
                autoUpdateStatus.style.background = '#1b4d1b';
                autoUpdateStatus.style.border = '1px solid #4CAF50';
                autoUpdateStatus.style.color = '#90EE90';  // Light green text
                autoUpdateStatus.innerHTML = `✅ <strong style="color:#4CAF50">Watcher running!</strong> Watching: <strong>${displayName}</strong><br>
                    <small style="color:#b0b0b0">PowerShell window opened. Keep it running while editing.</small>`;
            } else {
                autoUpdateStatus.style.background = '#4d1b1b';
                autoUpdateStatus.style.border = '1px solid #f44336';
                autoUpdateStatus.innerHTML = `❌ Failed to start watcher: ${result.error}`;
            }
        } catch (e) {
            autoUpdateStatus.style.background = '#4d1b1b';
            autoUpdateStatus.style.border = '1px solid #f44336';
            autoUpdateStatus.innerHTML = `❌ Error: ${e.message}`;
        }
    }

    function uploadFile(file) {
        // Show progress bar
        progressContainer.style.display = 'block';
        
        // Create FormData
        const formData = new FormData();
        formData.append('file', file);

        // Get the base URL
        const baseUrl = window.location.origin;
        
        // Check if auto-update is enabled
        const autoUpdateCheckbox = document.getElementById('autoUpdateCheckbox');
        const enableAutoUpdate = autoUpdateCheckbox && autoUpdateCheckbox.checked;

        // Upload file
        fetch(`${baseUrl}/upload`, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Upload response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Upload response data:', data);
            // Complete the progress bar
            progressBar.style.width = '100%';
            progressLabel.textContent = data.message;

            setTimeout(() => {
                progressContainer.style.display = 'none';
                progressBar.style.width = '0%';
                // Add the new map to the list with the actual filename
                addMapToList(data.filename);
            }, 1000);

            // Simulate double click on the actual saved file
            console.log('Starting simulate-click request...');
            const clickPath = `C:\\Users\\rust-\\AppData\\Roaming\\DDNet\\maps\\${data.filename}`;
            console.log('File path for simulate-click:', clickPath);
            
            fetch(`${baseUrl}/simulate-click`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filePath: clickPath
                })
            })
            .then(response => {
                console.log('Simulate-click response status:', response.status);
                return response.json();
            })
            .then(result => {
                console.log('Simulate-click result:', result);
                if (result.status === 'success') {
                    console.log('Successfully triggered map loading!');
                } else {
                    console.error('Simulate-click failed:', result.message);
                }
            })
            .catch(error => {
                console.error('Simulate-click error:', error);
            });
            
            // Start auto-update watcher if checkbox is enabled
            if (enableAutoUpdate) {
                startAutoUpdateWatcher(clickPath, data.originalName || file.name);
            }
        })
        .catch(error => {
            progressLabel.textContent = 'Upload failed';
            progressBar.style.backgroundColor = '#ff3333';
            setTimeout(() => {
                progressContainer.style.display = 'none';
                progressBar.style.width = '0%';
                progressBar.style.backgroundColor = 'var(--primary-color)';
            }, 2000);
        });
    }

    function addMapToList(mapName, timestamp = null, folder = '', size = null) {
        const mapItem = document.createElement('div');
        mapItem.className = 'map-item';
        
        const date = timestamp ? new Date(timestamp) : new Date();
        
        // Create download button
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'download-btn';
        downloadBtn.textContent = 'Download';
        downloadBtn.onclick = (e) => {
            e.stopPropagation();  // Prevent map click event
            downloadMap(mapName, folder);
        };
        
        // Show folder name if map is from a subfolder
        const folderLabel = folder ? `<span class="map-folder" style="color:#888;font-size:0.85em;margin-left:8px;">[${folder}]</span>` : '';
        
        // Format size
        const sizeLabel = size !== null ? `<span class="map-size" style="color:#888;font-size:0.85em;margin-left:8px;">${formatSize(size)}</span>` : '';
        
        mapItem.innerHTML = `
            <span class="map-name">${mapName}${folderLabel}${sizeLabel}</span>
            <span class="map-date">${date.toLocaleDateString()} ${date.toLocaleTimeString()}</span>
        `;
        mapItem.appendChild(downloadBtn);
        mapsList.appendChild(mapItem);
    }

    function downloadMap(mapName, folder = '') {
        const encodedName = encodeURIComponent(mapName).replace(/%20/g, ' ');
        const baseUrl = window.location.origin;
        const downloadPath = folder ? `${baseUrl}/download-folder/${encodeURIComponent(folder)}/${encodedName}` : `${baseUrl}/download/${encodedName}`;
        fetch(downloadPath)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        if (response.status === 404) {
                            let errorMsg = `File not found: ${data.path}`;
                            if (data.available_maps && data.available_maps.length > 0) {
                                errorMsg += '\n\nAvailable maps:\n' + data.available_maps.join('\n');
                            }
                            throw new Error(errorMsg);
                        } else if (response.status === 400) {
                            throw new Error('Invalid file name');
                        }
                        throw new Error(`Download failed: ${data.error}\nPath: ${data.path}\nMaps folder: ${data.maps_folder}`);
                    });
                }
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = mapName;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            })
            .catch(error => {
                alert(`Error: ${error.message}`);
                console.error('Download error:', error);
            });
    }

    // Click to select file
    dropZone.addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.map';
        input.onchange = e => {
            const file = e.target.files[0];
            handleFiles([file]);
        };
        input.click();
    });

    // Folder selector elements
    const folderSelect = document.getElementById('folderSelect');
    const refreshFoldersBtn = document.getElementById('refreshFolders');
    const sortBySelect = document.getElementById('sortBy');
    const sortOrderSelect = document.getElementById('sortOrder');
    let currentFolder = '';
    let currentMaps = []; // Store maps for sorting

    // Sort maps based on current settings
    function sortMaps(maps) {
        const sortBy = sortBySelect ? sortBySelect.value : 'date';
        const sortOrder = sortOrderSelect ? sortOrderSelect.value : 'desc';
        
        const sorted = [...maps].sort((a, b) => {
            let comparison = 0;
            switch (sortBy) {
                case 'name':
                    comparison = a.name.toLowerCase().localeCompare(b.name.toLowerCase());
                    break;
                case 'size':
                    comparison = (a.size || 0) - (b.size || 0);
                    break;
                case 'date':
                default:
                    comparison = (a.modified || 0) - (b.modified || 0);
                    break;
            }
            return sortOrder === 'asc' ? comparison : -comparison;
        });
        return sorted;
    }

    // Display maps with current sort
    function displayMaps() {
        mapsList.innerHTML = '';
        const sorted = sortMaps(currentMaps);
        sorted.forEach(map => {
            addMapToList(map.name, map.modified, map.folder, map.size);
        });
    }

    // Load folders from DDNet maps directory
    function loadFolders() {
        const baseUrl = window.location.origin;
        fetch(`${baseUrl}/list-folders`)
            .then(response => response.json())
            .then(folders => {
                // Keep the root option
                folderSelect.innerHTML = '<option value="">Root (maps/)</option>';
                folders.forEach(folder => {
                    const option = document.createElement('option');
                    option.value = folder.name;
                    option.textContent = `${folder.name} (${folder.mapCount} maps)`;
                    folderSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading folders:', error);
            });
    }

    // Load actual maps from the server
    function loadMaps(folder = '') {
        console.log('Attempting to load maps from folder:', folder || 'root');
        const baseUrl = window.location.origin;
        const endpoint = folder ? `${baseUrl}/list-maps-folder/${encodeURIComponent(folder)}` : `${baseUrl}/list-maps`;
        
        fetch(endpoint)
            .then(response => {
                console.log('Response status:', response.status);
                return response.json();
            })
            .then(maps => {
                console.log('Maps received:', maps);
                currentMaps = maps;
                displayMaps();
            })
            .catch(error => {
                console.error('Error loading maps:', error);
            });
    }

    // Handle folder selection change
    if (folderSelect) {
        folderSelect.addEventListener('change', () => {
            currentFolder = folderSelect.value;
            loadMaps(currentFolder);
        });
    }

    // Handle sort changes
    if (sortBySelect) {
        sortBySelect.addEventListener('change', displayMaps);
    }
    if (sortOrderSelect) {
        sortOrderSelect.addEventListener('change', displayMaps);
    }

    // Handle refresh button
    if (refreshFoldersBtn) {
        refreshFoldersBtn.addEventListener('click', () => {
            loadFolders();
            loadMaps(currentFolder);
        });
    }

    // Load folders and maps initially
    loadFolders();
    loadMaps();

    // Refresh maps list every 30 seconds
    setInterval(() => loadMaps(currentFolder), 30000);

    // ===== Auto-update checkbox =====
    const autoUpdateCheckbox = document.getElementById('autoUpdateCheckbox');
    const autoUpdateWarning = document.getElementById('autoUpdateWarning');

    // Show/hide warning when checkbox changes
    if (autoUpdateCheckbox) {
        autoUpdateCheckbox.addEventListener('change', () => {
            if (autoUpdateWarning) {
                autoUpdateWarning.style.display = autoUpdateCheckbox.checked ? 'block' : 'none';
            }
        });
    }
});
