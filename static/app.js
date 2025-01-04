// Calendar initialization
let calendar;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize calendar
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        editable: true,
        selectable: true,
        select: function(info) {
            showAddEventModal(info.start, info.end);
        },
        eventClick: function(info) {
            showEditEventModal(info.event);
        },
        events: function(fetchInfo, successCallback, failureCallback) {
            fetch('/api/calendar')
                .then(response => response.json())
                .then(events => {
                    const formattedEvents = events.map(event => ({
                        id: event.id,
                        title: event.title,
                        start: event.start,
                        end: event.end,
                        description: event.description,
                        backgroundColor: event.project_id ? getProjectColor(event.project_id) : undefined,
                        borderColor: event.project_id ? getProjectColor(event.project_id) : undefined,
                        extendedProps: {
                            project_id: event.project_id,
                            project_name: event.project_name,
                            event_type: event.event_type,
                            description: event.description
                        }
                    }));
                    console.log('Calendar events:', formattedEvents);  // Debug log
                    successCallback(formattedEvents);
                })
                .catch(error => {
                    console.error('Error fetching calendar events:', error);
                    failureCallback(error);
                });
        },
        eventDidMount: function(info) {
            if (info.event.extendedProps.event_type === 'task') {
                const projectId = info.event.extendedProps.project_id;
                if (projectId) {
                    const color = getProjectColor(projectId);
                    info.el.style.backgroundColor = color;
                    info.el.style.borderColor = color;
                }
            }
        }
    });
    calendar.render();

    // Load initial data
    loadProjects();
    loadTasks();
    loadBackups();
});

// Initialize Bootstrap tooltips and popovers
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});

// Modal handling
function showAddEventModal(start = null, end = null) {
    document.getElementById('eventModalTitle').textContent = 'Add Event';
    document.getElementById('eventId').value = '';
    document.getElementById('eventTitle').value = '';
    document.getElementById('eventDescription').value = '';
    document.getElementById('deleteEventBtn').style.display = 'none';
    
    if (start) {
        document.getElementById('eventStart').value = start.toLocalISOString();
    }
    if (end) {
        document.getElementById('eventEnd').value = end.toLocalISOString();
    }
    new bootstrap.Modal(document.getElementById('addEventModal')).show();
}

function showEditEventModal(event) {
    document.getElementById('eventModalTitle').textContent = 'Edit Event';
    document.getElementById('eventId').value = event.id;
    document.getElementById('eventTitle').value = event.title;
    document.getElementById('eventStart').value = event.start.toLocalISOString();
    document.getElementById('eventEnd').value = event.end.toLocalISOString();
    document.getElementById('eventDescription').value = event.extendedProps.description || '';
    document.getElementById('deleteEventBtn').style.display = 'block';
    
    new bootstrap.Modal(document.getElementById('addEventModal')).show();
}

function showAddProjectModal() {
    document.getElementById('projectModalTitle').textContent = 'Add Project';
    document.getElementById('projectId').value = '';
    document.getElementById('projectName').value = '';
    document.getElementById('projectDescription').value = '';
    document.getElementById('projectStatus').value = 'In Progress';
    document.getElementById('projectPriority').value = '3';
    document.getElementById('deleteProjectBtn').style.display = 'none';
    
    new bootstrap.Modal(document.getElementById('addProjectModal')).show();
}

function showEditProjectModal(project) {
    document.getElementById('projectModalTitle').textContent = 'Edit Project';
    document.getElementById('projectId').value = project.id;
    document.getElementById('projectName').value = project.name;
    document.getElementById('projectDescription').value = project.description || '';
    document.getElementById('projectStatus').value = project.status;
    document.getElementById('projectPriority').value = project.priority;
    document.getElementById('deleteProjectBtn').style.display = 'block';
    
    new bootstrap.Modal(document.getElementById('addProjectModal')).show();
}

async function showAddTaskModal() {
    const modal = new bootstrap.Modal(document.getElementById('addTaskModal'));
    
    // Clear previous values
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskDescription').value = '';
    document.getElementById('taskDuration').value = '';
    document.getElementById('taskPriority').value = '3';
    
    // Get projects for dropdown
    const response = await fetch('/api/projects');
    const projects = await response.json();
    
    const projectSelect = document.getElementById('taskProject');
    projectSelect.innerHTML = projects.map(project => 
        `<option value="${project.id}">${project.name}</option>`
    ).join('');
    
    modal.show();
}

function showEditTaskModal(task) {
    document.getElementById('taskModalTitle').textContent = 'Edit Task';
    document.getElementById('taskId').value = task.id;
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskDuration').value = task.estimated_duration;
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskStatus').value = task.status;
    document.getElementById('deleteTaskBtn').style.display = 'block';
    
    loadProjectsForTaskModal().then(() => {
        document.getElementById('taskProject').value = task.project_id;
    });
    
    new bootstrap.Modal(document.getElementById('addTaskModal')).show();
}

// Helper function to format datetime-local input
Date.prototype.toLocalISOString = function() {
    const offset = this.getTimezoneOffset();
    const local = new Date(this.getTime() - offset * 60 * 1000);
    return local.toISOString().slice(0, 16);
};

// API calls
async function saveEvent() {
    const eventId = document.getElementById('eventId').value;
    const event = {
        title: document.getElementById('eventTitle').value,
        start_time: document.getElementById('eventStart').value,
        end_time: document.getElementById('eventEnd').value,
        description: document.getElementById('eventDescription').value
    };

    try {
        const url = eventId ? `/api/calendar/${eventId}` : '/api/calendar';
        const method = eventId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(event)
        });

        if (response.ok) {
            location.reload();
        }
    } catch (error) {
        console.error('Error saving event:', error);
    }
}

async function deleteEvent() {
    const eventId = document.getElementById('eventId').value;
    if (!eventId) return;

    if (confirm('Are you sure you want to delete this event?')) {
        try {
            const response = await fetch(`/api/calendar/${eventId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                location.reload();
            }
        } catch (error) {
            console.error('Error deleting event:', error);
        }
    }
}

async function saveProject() {
    const projectId = document.getElementById('projectId').value;
    const project = {
        name: document.getElementById('projectName').value,
        description: document.getElementById('projectDescription').value,
        status: document.getElementById('projectStatus').value,
        priority: parseInt(document.getElementById('projectPriority').value)
    };

    try {
        const url = projectId ? `/api/projects/${projectId}` : '/api/projects';
        const method = projectId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(project)
        });

        if (response.ok) {
            loadProjects();
            bootstrap.Modal.getInstance(document.getElementById('addProjectModal')).hide();
        }
    } catch (error) {
        console.error('Error saving project:', error);
    }
}

async function deleteProject() {
    const projectId = document.getElementById('projectId').value;
    if (!projectId) return;

    if (confirm('Are you sure you want to delete this project? All associated tasks will also be deleted.')) {
        try {
            const response = await fetch(`/api/projects/${projectId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                loadProjects();
                loadTasks();
                bootstrap.Modal.getInstance(document.getElementById('addProjectModal')).hide();
            }
        } catch (error) {
            console.error('Error deleting project:', error);
        }
    }
}

async function saveTask() {
    const taskId = document.getElementById('taskId').value;
    const task = {
        project_id: document.getElementById('taskProject').value,
        title: document.getElementById('taskTitle').value,
        description: document.getElementById('taskDescription').value,
        estimated_duration: parseInt(document.getElementById('taskDuration').value),
        priority: parseInt(document.getElementById('taskPriority').value),
        status: document.getElementById('taskStatus').value
    };

    try {
        const url = taskId ? `/api/tasks/${taskId}` : '/api/tasks';
        const method = taskId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(task)
        });

        if (response.ok) {
            loadTasks();
            bootstrap.Modal.getInstance(document.getElementById('addTaskModal')).hide();
        }
    } catch (error) {
        console.error('Error saving task:', error);
    }
}

async function deleteTask() {
    const taskId = document.getElementById('taskId').value;
    if (!taskId) return;

    if (confirm('Are you sure you want to delete this task?')) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                loadTasks();
                bootstrap.Modal.getInstance(document.getElementById('addTaskModal')).hide();
            }
        } catch (error) {
            console.error('Error deleting task:', error);
        }
    }
}

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        displayProjects(projects);
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        displayTasks(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

async function loadProjectsForTaskModal() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        const select = document.getElementById('taskProject');
        select.innerHTML = projects.map(project => 
            `<option value="${project.id}">${project.name}</option>`
        ).join('');
    } catch (error) {
        console.error('Error loading projects for task modal:', error);
    }
}

// Track expanded project and task states
const expandedProjects = new Set();
const expandedTasks = new Set();

function toggleProjectDetails(projectId, event) {
    event.stopPropagation();
    expandedProjects.has(projectId) 
        ? expandedProjects.delete(projectId) 
        : expandedProjects.add(projectId);
    loadProjects();
}

function toggleTaskDetails(taskId, event) {
    event.stopPropagation();
    expandedTasks.has(taskId) 
        ? expandedTasks.delete(taskId) 
        : expandedTasks.add(taskId);
    loadTasks();
}

// Project color generation
const projectColors = {};

// Base colors with high saturation and good contrast
const baseColors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
    '#FFEEAD', '#D4A5A5', '#9B59B6', '#3498DB',
    '#FF8C42', '#29C7AC', '#6C5CE7', '#A8E6CF',
    '#FDCB6E', '#FF7675', '#74B9FF', '#55EDC4',
    '#2ECC71', '#F1C40F', '#E67E22', '#E84393'
];

// Generate a random color not in use
function generateUniqueColor() {
    // First try to use one of the base colors
    const unusedBaseColors = baseColors.filter(color => 
        !Object.values(projectColors).includes(color)
    );
    
    if (unusedBaseColors.length > 0) {
        return unusedBaseColors[Math.floor(Math.random() * unusedBaseColors.length)];
    }
    
    // If all base colors are used, generate a random color
    // that's sufficiently different from existing colors
    let newColor;
    let attempts = 0;
    const maxAttempts = 50;
    
    do {
        newColor = generateRandomColor();
        attempts++;
    } while (
        (isColorTooSimilarToExisting(newColor) || isColorTooDark(newColor)) && 
        attempts < maxAttempts
    );
    
    return newColor;
}

// Generate a random hex color
function generateRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// Convert hex to RGB
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

// Check if a color is too similar to existing colors
function isColorTooSimilarToExisting(newColor) {
    const existingColors = Object.values(projectColors);
    const newRgb = hexToRgb(newColor);
    
    return existingColors.some(existingColor => {
        const existingRgb = hexToRgb(existingColor);
        const distance = Math.sqrt(
            Math.pow(existingRgb.r - newRgb.r, 2) +
            Math.pow(existingRgb.g - newRgb.g, 2) +
            Math.pow(existingRgb.b - newRgb.b, 2)
        );
        return distance < 100; // Minimum distance threshold
    });
}

// Check if a color is too dark
function isColorTooDark(color) {
    const rgb = hexToRgb(color);
    const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
    return brightness < 128;
}

function getProjectColor(projectId) {
    if (!projectColors[projectId]) {
        projectColors[projectId] = generateUniqueColor();
    }
    return projectColors[projectId];
}

// Display functions
function displayProjects(projects) {
    const projectsList = document.getElementById('projects-list');
    projectsList.innerHTML = projects.map(project => {
        const projectColor = getProjectColor(project.id);
        const isExpanded = expandedProjects.has(project.id);
        return `
            <div class="project-item" onclick="showEditProjectModal(${JSON.stringify(project).replace(/"/g, '&quot;')})" 
                 style="border-left: 4px solid ${projectColor}">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <h5 class="mb-0">${project.name}</h5>
                        <span class="badge bg-${getStatusColor(project.status)} ms-2">${project.status}</span>
                        <span class="badge ${getPriorityClass(project.priority)} ms-2">${project.priority_label}</span>
                    </div>
                    <button class="btn btn-link btn-sm p-0 text-dark" 
                            onclick="toggleProjectDetails(${project.id}, event)">
                        <i class="fas fa-chevron-${isExpanded ? 'up' : 'down'}"></i>
                    </button>
                </div>
                <div class="project-details ${isExpanded ? 'show' : ''}" style="display: ${isExpanded ? 'block' : 'none'}">
                    <p class="mt-2 mb-2">${project.description || 'No description'}</p>
                    <div class="progress">
                        <div class="progress-bar" role="progressbar" 
                             style="width: ${project.progress || 0}%; background-color: ${projectColor}"
                             aria-valuenow="${project.progress || 0}" aria-valuemin="0" aria-valuemax="100">
                            ${project.progress || 0}%
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function displayTasks(tasks) {
    const tasksList = document.getElementById('tasks-list');
    tasksList.innerHTML = tasks.map(task => {
        const projectColor = getProjectColor(task.project_id);
        const isExpanded = expandedTasks.has(task.id);
        return `
            <div class="task-item" onclick="showEditTaskModal(${JSON.stringify(task).replace(/"/g, '&quot;')})"
                 style="border-left: 4px solid ${projectColor}">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center flex-grow-1">
                        <h6 class="mb-0 me-2">${task.title}</h6>
                        <span class="badge" style="background-color: ${projectColor}">${task.project_name}</span>
                        <span class="badge bg-${getStatusColor(task.status)} ms-2">${task.status}</span>
                        <span class="badge ${getPriorityClass(task.priority)} ms-2">${task.priority_label}</span>
                    </div>
                    <button class="btn btn-link btn-sm p-0 text-dark ms-2" 
                            onclick="toggleTaskDetails(${task.id}, event)">
                        <i class="fas fa-chevron-${isExpanded ? 'up' : 'down'}"></i>
                    </button>
                </div>
                <div class="task-details ${isExpanded ? 'show' : ''}" style="display: ${isExpanded ? 'block' : 'none'}">
                    <p class="mt-2 mb-2">${task.description || 'No description'}</p>
                    <small class="text-muted">Duration: ${task.estimated_duration} minutes</small>
                </div>
            </div>
        `;
    }).join('');
}

function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'completed':
            return 'success';
        case 'in progress':
            return 'primary';
        case 'pending':
            return 'warning';
        default:
            return 'secondary';
    }
}

function getPriorityClass(priority) {
    return {
        1: 'bg-danger',    // High priority
        2: 'bg-warning',   // Medium priority
        3: 'bg-info'       // Low priority
    }[priority] || 'bg-secondary';
}

// Backup Management Functions
let selectedBackupFile = null;

function loadBackups() {
    fetch('/api/backups')
        .then(response => response.json())
        .then(data => {
            const backupsList = document.getElementById('backups-list');
            backupsList.innerHTML = '';

            if (data.backups.length === 0) {
                backupsList.innerHTML = '<div class="list-group-item text-muted">No backups available</div>';
                return;
            }

            data.backups.forEach(backup => {
                const size = formatFileSize(backup.size);
                const backupItem = document.createElement('div');
                backupItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                backupItem.innerHTML = `
                    <div>
                        <h6 class="mb-1">${backup.filename}</h6>
                        <small class="text-muted">Created: ${backup.timestamp}</small>
                        <small class="text-muted ms-2">Size: ${size}</small>
                    </div>
                    <button class="btn btn-outline-primary btn-sm" onclick="showRestoreBackupModal('${backup.filename}', '${backup.timestamp}')">
                        <i class="fas fa-undo"></i> Restore
                    </button>
                `;
                backupsList.appendChild(backupItem);
            });
        })
        .catch(error => {
            console.error('Error loading backups:', error);
            showToast('Error', 'Failed to load backups', 'error');
        });
}

function createBackup() {
    fetch('/api/backups', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            showToast('Success', 'Backup created successfully', 'success');
            loadBackups();
        })
        .catch(error => {
            console.error('Error creating backup:', error);
            showToast('Error', 'Failed to create backup', 'error');
        });
}

function showRestoreBackupModal(filename, timestamp) {
    selectedBackupFile = filename;
    const details = document.getElementById('restore-backup-details');
    details.textContent = `Backup from: ${timestamp}`;
    const modal = new bootstrap.Modal(document.getElementById('restoreBackupModal'));
    modal.show();
}

function confirmRestoreBackup() {
    if (!selectedBackupFile) return;

    fetch(`/api/backups/restore/${selectedBackupFile}`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            showToast('Success', 'Database restored successfully', 'success');
            // Reload all data
            loadProjects();
            loadTasks();
            calendar.refetchEvents();
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('restoreBackupModal'));
            modal.hide();
        })
        .catch(error => {
            console.error('Error restoring backup:', error);
            showToast('Error', 'Failed to restore backup', 'error');
        });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// AI Functions
async function getAIAnalysis() {
    try {
        // Show loading state
        const aiSuggestions = document.getElementById('ai-suggestions');
        const aiContent = document.getElementById('ai-content');
        aiSuggestions.style.display = 'block';
        aiContent.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><div class="mt-2">Analyzing tasks and generating suggestions...</div></div>';

        // First get schedule suggestions
        const scheduleResponse = await fetch('/api/schedule/suggest');
        const scheduleData = await scheduleResponse.json();
        
        // Then get task dependencies analysis
        const analysisResponse = await fetch('/api/tasks/analyze');
        const analysisData = await analysisResponse.json();
        
        // Display the suggestions
        aiContent.innerHTML = `
            <div class="mb-4">
                <h6 class="mb-3">📅 Scheduling Suggestions</h6>
                <div class="list-group">
                    ${scheduleData.suggestions.map((suggestion, index) => `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 class="mb-1">${suggestion.task}</h6>
                                    <p class="mb-1 text-muted small">
                                        <i class="fas fa-clock"></i> ${formatDateTime(suggestion.suggested_time)}
                                    </p>
                                    <p class="mb-1 small">
                                        <i class="fas fa-info-circle"></i> ${suggestion.reason}
                                    </p>
                                </div>
                                <button class="btn btn-outline-success btn-sm" 
                                        onclick="handleSuggestionApproval(${index})">
                                    <i class="fas fa-check"></i> Schedule
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div>
                <h6 class="mb-3">🔄 Task Dependencies</h6>
                <pre class="border rounded p-3 bg-light" style="font-size: 0.8rem; white-space: pre-wrap;">${analysisData.analysis}</pre>
            </div>
        `;

        // Store suggestions in a global variable for reference
        window.currentSuggestions = scheduleData.suggestions;
    } catch (error) {
        console.error('Error getting AI analysis:', error);
        alert('Error getting AI suggestions. Please try again.');
    }
}

async function handleSuggestionApproval(index) {
    const suggestion = window.currentSuggestions[index];
    if (!suggestion) {
        console.error('Suggestion not found');
        return;
    }

    const button = event.target.closest('button');
    if (button.disabled) return;

    try {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scheduling...';

        const response = await fetch('/api/schedule/approve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task: suggestion.task,
                suggested_time: suggestion.suggested_time,
                duration: 60
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Refresh the calendar events
            calendar.refetchEvents();
            
            // Update button state
            button.innerHTML = '<i class="fas fa-check"></i> Scheduled';
            button.classList.remove('btn-outline-success');
            button.classList.add('btn-success');
            
            // Show success message
            showToast('Success', 'Task has been scheduled!', 'success');
        } else {
            throw new Error(data.error || 'Failed to approve suggestion');
        }
    } catch (error) {
        console.error('Error approving suggestion:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-check"></i> Schedule';
        showToast('Error', 'Failed to schedule task. Please try again.', 'error');
    }
}

function formatDateTime(dateTimeStr) {
    const date = new Date(dateTimeStr);
    return date.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

function showToast(title, message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong><br>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
}

function closeAISuggestions() {
    document.getElementById('ai-suggestions').style.display = 'none';
}
