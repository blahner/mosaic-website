// Mock data - replace with actual S3 API calls
const mockData = [
    {
        fileId: "dataset1_subject1_pipeline1.hdf5",
        datasetName: "Neural Activity Dataset",
        subjectName: "Subject_001",
        pipeline: "preprocessing_v1",
        ownerName: "Dr. Smith",
        ownerEmail: "smith@university.edu",
        trialFormat: "continuous",
        githubUrl: "https://github.com/lab/neural-analysis",
        publicationUrl: "https://doi.org/10.1000/example1"
    },
    {
        fileId: "dataset1_subject2_pipeline1.hdf5",
        datasetName: "Neural Activity Dataset",
        subjectName: "Subject_002",
        pipeline: "preprocessing_v1",
        ownerName: "Dr. Smith",
        ownerEmail: "smith@university.edu",
        trialFormat: "continuous",
        githubUrl: "https://github.com/lab/neural-analysis",
        publicationUrl: "https://doi.org/10.1000/example1"
    },
    {
        fileId: "dataset1_subject1_pipeline2.hdf5",
        datasetName: "Neural Activity Dataset",
        subjectName: "Subject_001",
        pipeline: "preprocessing_v2",
        ownerName: "Dr. Smith",
        ownerEmail: "smith@university.edu",
        trialFormat: "continuous",
        githubUrl: "https://github.com/lab/neural-analysis",
        publicationUrl: "https://doi.org/10.1000/example1"
    },
    {
        fileId: "dataset2_subject1_pipeline1.hdf5",
        datasetName: "Behavioral Dataset",
        subjectName: "Subject_A",
        pipeline: "analysis_standard",
        ownerName: "Dr. Johnson",
        ownerEmail: "johnson@institute.org",
        trialFormat: "discrete",
        githubUrl: "https://github.com/lab/behavior-analysis",
        publicationUrl: "https://doi.org/10.1000/example2"
    }
];

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

/*
// In a real implementation, this would fetch from S3
function loadData() {
    allData = mockData;
    displayData(allData);
    updateStats();
}
    */

function groupData(data) {
    const groups = new Map();
    
    data.forEach(item => {
        const groupKey = `${item.datasetName}|${item.pipeline}|${item.trialFormat}|${item.publicationUrl}|${item.githubUrl}`;
        
        if (!groups.has(groupKey)) {
            groups.set(groupKey, {
                metadata: {
                    datasetName: item.datasetName,
                    pipeline: item.pipeline,
                    ownerName: item.ownerName,
                    ownerEmail: item.ownerEmail,
                    trialFormat: item.trialFormat,
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
                    <span class="metadata-label">Pipeline</span>
                    <span class="metadata-value">${group.metadata.pipeline}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Owner</span>
                    <span class="metadata-value">${group.metadata.ownerName} (${group.metadata.ownerEmail})</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Trial Format</span>
                    <span class="metadata-value">${group.metadata.trialFormat}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">GitHub</span>
                    <span class="metadata-value"><a href="${group.metadata.githubUrl}" target="_blank">${group.metadata.githubUrl}</a></span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Publication</span>
                    <span class="metadata-value"><a href="${group.metadata.publicationUrl}" target="_blank">${group.metadata.publicationUrl}</a></span>
                </div>
            </div>
        </div>
        <div class="objects-list">
            ${group.files.map(file => createFileElement(file)).join('')}
        </div>
    `;
    
    return groupDiv;
}

function createFileElement(file) {
    return `
        <div class="object-item">
            <input type="checkbox" class="object-checkbox" data-file-id="${file.fileId}" 
                   onchange="toggleFileSelection('${file.fileId}')">
            <div class="object-info">
                <span class="object-id">${file.fileId}</span>
                <span>${file.subjectName}</span>
                <span>${file.ownerName}</span>
                <span>${file.trialFormat}</span>
            </div>
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
        item.subjectName.toLowerCase().includes(searchTerm) ||
        item.pipeline.toLowerCase().includes(searchTerm) ||
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