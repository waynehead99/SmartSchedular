// Calendar initialization
let calendar;

// Initialize event listeners when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadTasks();
    initializeCalendar();
    setupEventListeners();
});

function setupEventListeners() {
    // Status Report button
    const statusReportBtn = document.getElementById('generateStatusReportBtn');
    if (statusReportBtn) {
        statusReportBtn.addEventListener('click', generateStatusReport);
    }
    
    // Other event listeners...
}

// Initialize calendar
function initializeCalendar() {
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
}

// Load initial data
loadProjects();
loadBackups();

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
    
    // Load available projects for selection
    loadProjectsForTaskModal();
    
    // Load available tasks for dependencies
    loadTasksForDependencies();
    
    modal.show();
}

function showEditTaskModal(task) {
    const modal = document.getElementById('editTaskModal');
    const form = modal.querySelector('form');
    
    // Populate form fields
    form.querySelector('#editTaskTitle').value = task.title;
    form.querySelector('#editTaskDescription').value = task.description;
    form.querySelector('#editTaskTicketNumber').value = task.ticket_number || '';
    form.querySelector('#editTaskPriority').value = task.priority;
    form.querySelector('#editTaskStatus').value = task.status;
    form.querySelector('#editTaskDuration').value = task.estimated_duration || '';
    
    // Load and display status history
    loadStatusHistory(task.id);
    
    // Store task ID for form submission
    form.dataset.taskId = task.id;
    
    // Show modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

function loadStatusHistory(taskId) {
    fetch(`/api/tasks/${taskId}/status-history`)
        .then(response => response.json())
        .then(data => {
            const historyContainer = document.getElementById('statusHistory');
            historyContainer.innerHTML = '';
            
            if (data.status_updates && data.status_updates.length > 0) {
                const timeline = document.createElement('div');
                timeline.className = 'status-timeline';
                
                data.status_updates.forEach(update => {
                    const updateItem = document.createElement('div');
                    updateItem.className = 'status-update-item';
                    
                    const date = new Date(update.created_at);
                    updateItem.innerHTML = `
                        <div class="status-badge ${getStatusColor(update.status)}">
                            ${update.status}
                        </div>
                        <div class="status-details">
                            <div class="status-time">
                                ${date.toLocaleString()}
                            </div>
                            ${update.notes ? `<div class="status-notes">${update.notes}</div>` : ''}
                        </div>
                    `;
                    
                    timeline.appendChild(updateItem);
                });
                
                historyContainer.appendChild(timeline);
            } else {
                historyContainer.innerHTML = '<p class="text-muted">No status updates yet</p>';
            }
        })
        .catch(error => {
            console.error('Error loading status history:', error);
            showToast('Error', 'Failed to load status history', 'error');
        });
}

function updateTaskStatus() {
    const modal = document.getElementById('editTaskModal');
    const form = modal.querySelector('form');
    const taskId = form.dataset.taskId;
    const status = form.querySelector('#editTaskStatus').value;
    const notes = form.querySelector('#statusNotes').value;
    
    fetch(`/api/tasks/${taskId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            status: status,
            notes: notes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        showToast('Success', 'Status updated successfully', 'success');
        loadTasks();  // Refresh task list
        loadStatusHistory(taskId);  // Refresh status history
        form.querySelector('#statusNotes').value = '';  // Clear notes field
    })
    .catch(error => {
        console.error('Error updating status:', error);
        showToast('Error', 'Failed to update status', 'error');
    });
}

async function loadTasksForDependencies(excludeTaskId = null) {
    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        const select = document.getElementById('taskDependencies');
        select.innerHTML = '';
        
        tasks.forEach(task => {
            if (task.id !== excludeTaskId) {  // Don't show current task as dependency option
                const option = document.createElement('option');
                option.value = task.id;
                option.textContent = `${task.title} (${task.status})`;
                select.appendChild(option);
            }
        });
    } catch (error) {
        console.error('Error loading tasks for dependencies:', error);
        showToast('Error', 'Failed to load tasks for dependencies', 'error');
    }
}

async function loadProjectsForTaskModal() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        const select = document.getElementById('taskProject');
        select.innerHTML = `
            <option value="" disabled selected>Select a project</option>
            ${projects.map(project => 
                `<option value="${project.id}">${project.name}</option>`
            ).join('')}
        `;
    } catch (error) {
        console.error('Error loading projects for task modal:', error);
        showToast('Error', 'Failed to load projects', 'error');
    }
}

async function saveTask() {
    const modal = document.getElementById('editTaskModal');
    const form = modal.querySelector('form');
    const taskId = form.dataset.taskId;
    
    const data = {
        title: form.querySelector('#editTaskTitle').value,
        description: form.querySelector('#editTaskDescription').value,
        ticket_number: form.querySelector('#editTaskTicketNumber').value,
        priority: parseInt(form.querySelector('#editTaskPriority').value),
        status: form.querySelector('#editTaskStatus').value,
        estimated_duration: parseInt(form.querySelector('#editTaskDuration').value) || null
    };
    
    fetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        showToast('Success', 'Task updated successfully', 'success');
        loadTasks();  // Refresh task list
        bootstrap.Modal.getInstance(modal).hide();
    })
    .catch(error => {
        console.error('Error saving task:', error);
        showToast('Error', 'Failed to save task changes', 'error');
    });
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
            showToast('Error', 'Failed to delete task', 'error');
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

function displayTasks(tasks) {
    const tasksList = document.getElementById('tasks-list');
    tasksList.innerHTML = '';
    
    tasks.forEach(task => {
        const taskItem = document.createElement('div');
        taskItem.className = 'list-group-item task-item';
        
        // Add background color based on status
        taskItem.style.backgroundColor = getStatusBackground(task.status);
        
        // Add left border color based on project color
        if (task.project_id) {
            const projectColor = getProjectColor(task.project_id);
            taskItem.style.borderLeft = `4px solid ${projectColor}`;
        }
        
        const taskHeader = document.createElement('div');
        taskHeader.className = 'd-flex justify-content-between align-items-start';
        
        const taskContent = document.createElement('div');
        taskContent.className = 'ms-2 me-auto';
        
        const titleRow = document.createElement('div');
        titleRow.className = 'd-flex align-items-center gap-2';
        
        const title = document.createElement('div');
        title.className = 'fw-bold';
        title.textContent = task.title;
        
        const statusBadge = document.createElement('span');
        statusBadge.className = `badge ${getStatusColor(task.status)} badge-sm`;
        statusBadge.textContent = task.status;
        
        titleRow.appendChild(title);
        titleRow.appendChild(statusBadge);
        
        const projectName = document.createElement('small');
        projectName.className = 'text-muted d-block mt-1';
        projectName.textContent = task.project_name;
        if (task.project_id) {
            const projectColor = getProjectColor(task.project_id);
            projectName.style.color = projectColor;
        }
        
        const priorityBadge = document.createElement('span');
        priorityBadge.className = `badge ${getPriorityClass(task.priority)} ms-2`;
        priorityBadge.textContent = task.priority_label;
        
        // Add progress bar if task is in progress
        if (task.status === 'In Progress') {
            const progressBar = document.createElement('div');
            progressBar.className = 'progress mt-2';
            progressBar.style.height = '5px';
            
            const progressBarInner = document.createElement('div');
            progressBarInner.className = 'progress-bar';
            progressBarInner.style.width = `${task.progress}%`;
            if (task.project_id) {
                progressBarInner.style.backgroundColor = getProjectColor(task.project_id);
            }
            
            progressBar.appendChild(progressBarInner);
            taskContent.appendChild(progressBar);
        }
        
        // Create task actions container
        const taskActions = document.createElement('div');
        taskActions.className = 'task-actions d-flex align-items-center';
        
        // Build the task item structure
        taskContent.appendChild(titleRow);
        taskContent.appendChild(projectName);
        
        taskHeader.appendChild(taskContent);
        taskHeader.appendChild(taskActions);
        taskHeader.appendChild(priorityBadge);
        
        taskItem.appendChild(taskHeader);
        
        // Add click handler to task content area only
        taskContent.addEventListener('click', (e) => {
            e.stopPropagation();
            showEditTaskModal(task);
        });
        
        // Add schedule button
        addScheduleButton(taskItem, task);
        
        tasksList.appendChild(taskItem);
    });
}

// Add schedule button to task items
function addScheduleButton(taskItem, task) {
    const scheduleButton = document.createElement('button');
    scheduleButton.className = 'btn btn-sm btn-outline-primary ms-2';
    scheduleButton.innerHTML = '<i class="fas fa-calendar-alt"></i>';
    scheduleButton.title = 'Get AI scheduling suggestions';
    
    scheduleButton.addEventListener('click', async (event) => {
        event.stopPropagation(); // Stop event from bubbling up
        try {
            const response = await fetch('/api/schedule/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: task.id
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to get scheduling suggestions');
            }
            
            const data = await response.json();
            if (data.suggestions && data.suggestions.length > 0) {
                showSchedulingSuggestions(data.suggestions, task);
            } else {
                showToast('Info', 'No scheduling suggestions available at this time.', 'info');
            }
        } catch (error) {
            console.error('Error getting scheduling suggestions:', error);
            showToast('Error', 'Error getting scheduling suggestions. Please try again.', 'error');
        }
    });
    
    taskItem.querySelector('.task-actions').appendChild(scheduleButton);
}

function showSchedulingSuggestions(suggestions, task) {
    // Create modal content
    const modalContent = document.createElement('div');
    modalContent.innerHTML = `
        <div class="modal fade" id="schedulingModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Scheduling Suggestions for "${task.title}"</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="list-group">
                            ${suggestions.map(suggestion => `
                                <div class="list-group-item">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div>
                                            <h6 class="mb-1">Suggested Time: ${suggestion.suggested_time}</h6>
                                            <p class="mb-1 text-muted">Duration: ${suggestion.duration} minutes</p>
                                            <p class="mb-1 small text-muted">${suggestion.reason}</p>
                                        </div>
                                        <button class="btn btn-sm btn-success schedule-time-btn" 
                                                data-time="${suggestion.suggested_time}"
                                                data-duration="${suggestion.duration}">
                                            Schedule
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove any existing modal
    const existingModal = document.getElementById('schedulingModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to document
    document.body.appendChild(modalContent.firstElementChild);
    
    // Initialize modal
    const modal = new bootstrap.Modal(document.getElementById('schedulingModal'));
    modal.show();
    
    // Add event listeners to schedule buttons
    document.querySelectorAll('.schedule-time-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const scheduledTime = button.dataset.time;
            const duration = parseInt(button.dataset.duration, 10);
            
            try {
                const response = await fetch('/api/schedule/approve', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task_id: task.id,
                        suggested_time: scheduledTime,
                        duration: duration
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to schedule task');
                }
                
                const data = await response.json();
                showToast('Success', `Task scheduled for ${scheduledTime}`, 'success');
                modal.hide();
                loadTasks(); // Refresh task list
                if (calendar) calendar.refetchEvents(); // Refresh calendar if it exists
            } catch (error) {
                console.error('Error scheduling task:', error);
                showToast('Error', 'Error scheduling task. Please try again.', 'error');
            }
        });
    });
}

async function generateSchedule() {
    try {
        showLoadingToast('Generating schedule suggestions...');
        
        const response = await fetch('/api/schedule/suggest', {
            method: 'GET'
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate schedule');
        }
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Display suggestions in the modal
        const suggestionsDiv = document.getElementById('scheduleSuggestions');
        if (data.suggestions && data.suggestions.length > 0) {
            const suggestionsHtml = data.suggestions.map(suggestion => `
                <div class="suggestion-item mb-3">
                    <h5>${suggestion.task}</h5>
                    <p><strong>Suggested Time:</strong> ${suggestion.suggested_time}</p>
                    <p><strong>Reason:</strong> ${suggestion.reason}</p>
                    <button class="btn btn-sm btn-success" onclick="acceptScheduleSuggestion('${suggestion.task}', '${suggestion.suggested_time}')">
                        Accept
                    </button>
                </div>
            `).join('');
            
            suggestionsDiv.innerHTML = `
                <div class="alert alert-info">
                    Here are your AI-powered schedule suggestions:
                </div>
                ${suggestionsHtml}
            `;
        } else {
            suggestionsDiv.innerHTML = `
                <div class="alert alert-warning">
                    No schedule suggestions available at this time. This might be because:
                    <ul>
                        <li>All tasks are already scheduled or completed</li>
                        <li>No suitable time slots were found</li>
                        <li>Tasks don't have estimated durations set</li>
                    </ul>
                </div>
            `;
        }
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('scheduleModal'));
        modal.show();
        
        hideLoadingToast();
        showToast('Success', 'Schedule suggestions generated successfully', 'success');
    } catch (error) {
        console.error('Error generating schedule:', error);
        hideLoadingToast();
        showToast('Error', error.message || 'Failed to generate schedule', 'error');
    }
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(event)
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to save event');
        }

        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addEventModal'));
        if (modal) {
            modal.hide();
        }

        // Refresh the calendar events
        calendar.refetchEvents();
        
        // Show success message
        showToast('Success', 'Event saved successfully', 'success');
    } catch (error) {
        console.error('Error saving event:', error);
        showToast('Error', error.message || 'Failed to save event', 'error');
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
            headers: { 'Content-Type': 'application/json' },
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
                    <div>
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

function getStatusBackground(status) {
    switch (status) {
        case 'Not Started':
            return '#f8f9fa';  // Light gray
        case 'In Progress':
            return '#e8f4ff';  // Light blue
        case 'Completed':
            return '#e8f8e8';  // Light green
        default:
            return '#ffffff';  // White
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

        // Get task dependencies analysis
        const analysisResponse = await fetch('/api/tasks/analyze');
        const analysisData = await analysisResponse.json();
        
        // Display the suggestions
        aiContent.innerHTML = `
            <div>
                <h6 class="mb-3">🔄 Task Dependencies Analysis</h6>
                <pre class="border rounded p-3 bg-light" style="font-size: 0.8rem; white-space: pre-wrap;">${analysisData.analysis}</pre>
            </div>
            <div class="mt-4">
                <p class="text-muted">
                    <i class="fas fa-info-circle"></i> 
                    Click the calendar icon on any task to get AI scheduling suggestions for that specific task.
                </p>
            </div>
        `;
    } catch (error) {
        console.error('Error getting AI analysis:', error);
        aiContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i> 
                Error analyzing tasks. Please try again.
            </div>
        `;
    }
}

// Loading state management
let loadingToast = null;

function showLoadingToast(message) {
    hideLoadingToast(); // Clear any existing toast
    loadingToast = showToast('Loading', message, 'info', false);
}

function hideLoadingToast() {
    if (loadingToast) {
        loadingToast.hide();
        loadingToast = null;
    }
}

async function generateStatusReport() {
    let loadingToast = null;
    try {
        loadingToast = showToast('Loading', 'Generating status report...', 'info', false);
        console.log('Generating status report...'); // Debug log
        
        const response = await fetch('/api/status-report');
        console.log('Response received:', response.status); // Debug log
        
        if (!response.ok) {
            throw new Error(`Failed to generate status report: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Data received:', data); // Debug log
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Convert markdown to HTML using marked
        const reportHtml = marked.parse(data.report);
        
        // Display the report in the modal
        const reportContent = document.getElementById('statusReportContent');
        reportContent.innerHTML = reportHtml;
        
        // Show the modal
        const modal = document.getElementById('statusReportModal');
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        if (loadingToast) {
            loadingToast.hide();
        }
        showToast('Success', 'Status report generated successfully', 'success');
    } catch (error) {
        console.error('Error generating status report:', error);
        if (loadingToast) {
            loadingToast.hide();
        }
        showToast('Error', error.message || 'Failed to generate status report', 'error');
    }
}

async function copyStatusReport() {
    try {
        const reportContent = document.getElementById('statusReportContent');
        const textContent = reportContent.innerText;
        await navigator.clipboard.writeText(textContent);
        showToast('Success', 'Report copied to clipboard', 'success');
    } catch (error) {
        console.error('Error copying report:', error);
        showToast('Error', 'Failed to copy report', 'error');
    }
}

function showToast(title, message, type = 'info', autohide = true) {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong>: ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { 
        autohide: autohide,
        delay: 3000  // Always set a delay, even if autohide is false
    });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
    
    return bsToast;
}

function closeAISuggestions() {
    document.getElementById('ai-suggestions').style.display = 'none';
}
