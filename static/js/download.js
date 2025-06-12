
let selectedFiles = new Set();
let allData = [];

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('input', filterData);
    document.getElementById('copyButton').addEventListener('click', copyScript);
}


// Load data from Flask API
async function loadData() {
    try {
        const response = await fetch(`api/s3/files`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        allData = data;
        displayData(allData);
        updateStats();
    } catch (error) {
        console.error('Error loading data:', error);
        // Show error message to user
        const container = document.getElementById('datasetGroups');
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #666;">
                <h3>Error Loading Data</h3>
                <p>Failed to load files from S3. Please check if the Flask server is running.</p>
                <p style="font-size: 0.9rem; margin-top: 1rem;">Error: ${error.message}</p>
            </div>
        `;
    }
}

function groupData(data) {
    const groups = new Map();
    
    data.forEach(item => {
        const groupKey = `${item.datasetName}|${item.preprocessingPipeline}|${item.betaPipeline}|${item.publicationUrl}`;
        
        if (!groups.has(groupKey)) {
            groups.set(groupKey, {
                metadata: {
                    datasetName: item.datasetName,
                    preprocessingPipeline: item.preprocessingPipeline,
                    ownerName: item.ownerName,
                    ownerEmail: item.ownerEmail,
                    betaPipeline: item.betaPipeline,
                    githubUrl: item.githubUrl,
                    publicationUrl: item.publicationUrl
                },
                files: []
            });
        }
        
        groups.get(groupKey).files.push(item);
    });
    
    return Array.from(groups.values());
}

function displayData(data) {
    const container = document.getElementById('datasetGroups');
    const groups = groupData(data);
    
    container.innerHTML = '';
    
    groups.forEach(group => {
        const groupElement = createGroupElement(group);
        container.appendChild(groupElement);
    });
}

function createGroupElement(group) {
    const groupDiv = document.createElement('div');
    groupDiv.className = 'dataset-group';
    
    groupDiv.innerHTML = `
        <div class="group-header">
            <div class="group-title">${group.metadata.datasetName}</div>
            <div class="group-metadata">
                <div class="metadata-item">
                    <span class="metadata-label">Preprocessing Pipeline</span>
                    <span class="metadata-value">${group.metadata.preprocessingPipeline}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Beta Pipeline</span>
                    <span class="metadata-value">${group.metadata.betaPipeline}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Publication URL</span>
                    <span class="metadata-value" style="word-break: break-all;"><a href="${group.metadata.publicationUrl}" target="_blank">${group.metadata.publicationUrl}</a></span>
                </div>
            </div>
        </div>
        <div class="objects-list">
            <div class="file-headers" style="display: grid; grid-template-columns: 40px 2fr 100px 200px 1fr; gap: 1rem; padding: 0.5rem; font-weight: bold; border-bottom: 1px solid #ddd; margin-bottom: 0.5rem;">
                <span></span>
                <span>File ID</span>
                <span>Size</span>
                <span>Owner</span>
                <span>GitHub</span>
            </div>
            ${group.files.map(file => createFileElement(file)).join('')}
        </div>
    `;
    
    return groupDiv;
}

function createFileElement(file) {
    return `
        <div class="object-item" style="display: grid; grid-template-columns: 40px 2fr 100px 200px 1fr; gap: 1rem; align-items: center; padding: 0.5rem;">
            <input type="checkbox" class="object-checkbox" data-file-id="${file.fileId}" 
                   onchange="toggleFileSelection('${file.fileId}')">
            <span style="word-break: break-all;">${file.fileId}</span>
            <span>${file.size}</span>
            <span>${file.ownerName} (${file.ownerEmail})</span>
            <span style="word-break: break-all;"><a href="${file.githubUrl}" target="_blank">${file.githubUrl}</a></span>
        </div>
    `;
}

function toggleFileSelection(fileId) {
    if (selectedFiles.has(fileId)) {
        selectedFiles.delete(fileId);
    } else {
        selectedFiles.add(fileId);
    }
    
    updateDownloadScript();
    updateStats();
}

function updateDownloadScript() {
    const scriptElement = document.getElementById('downloadScript');
    
    if (selectedFiles.size === 0) {
        scriptElement.textContent = `#!/bin/bash
# No files selected
echo "Please select files to download"`;
        return;
    }
    
    const fileList = Array.from(selectedFiles);
    const script = `#!/bin/bash
# Download script for selected files into your current directory
# Total files: ${fileList.length}

CLOUDFRONT_URL="https://d3ctas52djku5l.cloudfront.net"
FILES=(
${fileList.map(file => `    "${file}"`).join('\n')}
)

echo "Downloading ${fileList.length} files..."

for file in "\${FILES[@]}"; do
    echo "Downloading \$file..."
    curl -L -o "./\$file" "\$CLOUDFRONT_URL/\$file"
    if [ $? -eq 0 ]; then
        echo "✓ Successfully downloaded \$file"
    else
        echo "✗ Failed to download \$file"
    fi
done

echo "Download complete!"`;
    
    scriptElement.textContent = script;
}

function filterData() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    if (!searchTerm) {
        displayData(allData);
        return;
    }
    
    const filteredData = allData.filter(item => 
        item.datasetName.toLowerCase().includes(searchTerm) ||
        item.preprocessingPipeline.toLowerCase().includes(searchTerm) ||
        item.betaPipeline.toLowerCase().includes(searchTerm) ||
        item.githubUrl.toLowerCase().includes(searchTerm) ||
        item.ownerName.toLowerCase().includes(searchTerm) ||
        item.fileId.toLowerCase().includes(searchTerm)
    );
    
    displayData(filteredData);
    updateStats();
}

function updateStats() {
    const groups = groupData(allData);
    const totalFiles = allData.length;
    const selectedCount = selectedFiles.size;
    
    document.getElementById('statsDisplay').textContent = 
        `${groups.length} datasets, ${totalFiles} files (${selectedCount} selected)`;
}

function copyScript() {
    const scriptText = document.getElementById('downloadScript').textContent;
    navigator.clipboard.writeText(scriptText).then(() => {
        const button = document.getElementById('copyButton');
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    });
}