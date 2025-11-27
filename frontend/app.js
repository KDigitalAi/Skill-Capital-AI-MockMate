/**
 * Skill Capital AI MockMate - Frontend
 * Lightweight JavaScript for simple, clean interface
 * 
 * NOTE: This file requires api-config.js to be loaded first
 * api-config.js provides: getApiBase(), ensureApiBaseReady(), API_BASE
 */

// API configuration is provided by api-config.js
// Use getApiBase() function to get the API base URL
// Use ensureApiBaseReady() to wait for API config to be ready

// State
let currentUserId = null;
let currentSessionId = null;
let currentQuestionNum = 0;
let totalQuestions = 0;
let interviewMode = 'text';
let timerInterval = null;
let timeRemaining = 60;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    init();
});

// Also reload profile when page becomes visible (user returns from resume analysis page)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Check if we have a user_id and reload profile
        const userId = currentUserId || window.CURRENT_USER_ID || 
                      localStorage.getItem('user_id') || 
                      sessionStorage.getItem('resume_user_id');
        if (userId) {
            loadProfile();
        }
    }
});

// Get current authenticated user from user_profiles (optional - won't fail if no user exists)
async function getCurrentUser() {
    try {
        const res = await fetch(`${getApiBase()}/api/profile/current`);
        if (!res.ok) {
            if (res.status === 404) {
                // No user found - this is OK for new users
                console.log('No existing user profile found - new user can upload resume');
                return null;
            }
            throw new Error(`Failed to get current user: ${res.status}`);
        }
        const user = await res.json();
        currentUserId = user.user_id;
        window.CURRENT_USER_ID = currentUserId; // Store globally for other scripts
        
        // Store in localStorage for persistence
        if (currentUserId) {
            localStorage.setItem('user_id', currentUserId);
            sessionStorage.setItem('resume_user_id', currentUserId);
        }
        
        console.log('Current user found:', currentUserId);
        return user;
    } catch (e) {
        // Network error or other issue - don't throw, just log
        console.log('Could not fetch current user (this is OK for new users):', e.message);
        return null;
    }
}

async function init() {
    console.log('Initializing app...');
    // Always set up event listeners first - this is critical for upload to work
    // Use setTimeout to ensure DOM is fully ready
    setTimeout(() => {
        console.log('Setting up event listeners after DOM ready...');
        setupEventListeners();
    }, 100);
    
    try {
        // Try to get current authenticated user (optional - don't fail if no user exists)
        const user = await getCurrentUser();
        if (user && currentUserId) {
            console.log('User found from API, loading profile and dashboard');
            // Load profile if user exists
            loadProfile();
            // Load dashboard if user exists
            loadDashboard();
        } else {
            console.log('No user found from API - checking storage for user_id');
            // Get user_id from storage (backend generates it from resume name)
            // DO NOT generate UUID - wait for backend to create user_id from resume
            if (!currentUserId && !window.CURRENT_USER_ID) {
                const storedUserId = localStorage.getItem('user_id') || sessionStorage.getItem('resume_user_id');
                if (storedUserId) {
                    currentUserId = storedUserId;
                    window.CURRENT_USER_ID = storedUserId;
                } else {
                    console.log('No user_id in storage yet. User needs to upload resume first.');
                }
            }
            
            // Always try to load profile - loadProfile() will handle the case when there's no user_id
            // It will show appropriate message or fetch profile if user_id exists
            loadProfile();
            // Also try to load dashboard if we have a user_id
            if (currentUserId || window.CURRENT_USER_ID) {
                loadDashboard();
            }
        }
    } catch (e) {
        console.error('Initialization error:', e);
        // Don't block the UI - still allow upload
        // Get user_id from storage (backend generates it from resume name)
        // DO NOT generate UUID - wait for backend to create user_id from resume
        if (!currentUserId && !window.CURRENT_USER_ID) {
            const storedUserId = localStorage.getItem('user_id') || sessionStorage.getItem('resume_user_id');
            if (storedUserId) {
                currentUserId = storedUserId;
                window.CURRENT_USER_ID = storedUserId;
                console.log('Retrieved user_id from storage after error:', storedUserId);
            } else {
                console.log('No user_id in storage. User needs to upload resume first.');
            }
        }
        
        // Always try to load profile even after error - loadProfile() handles errors gracefully
        loadProfile();
        // Also try to load dashboard if we have a user_id
        if (currentUserId || window.CURRENT_USER_ID) {
            loadDashboard();
        }
    }
}

function setupEventListeners() {
    // File upload - check if elements exist before attaching listeners
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadArea = document.getElementById('uploadArea');

    console.log('Setting up event listeners...');
    console.log('fileInput found:', !!fileInput);
    console.log('uploadBtn found:', !!uploadBtn);
    console.log('uploadArea found:', !!uploadArea);

    if (fileInput && uploadBtn) {
        // Ensure file input is accessible and not disabled
        if (fileInput) {
            fileInput.disabled = false;
            fileInput.removeAttribute('disabled');
            fileInput.style.display = 'none'; // Hide but keep accessible
            console.log('File input is ready, disabled:', fileInput.disabled);
        }
        
        // Ensure file input is always ready
        fileInput.disabled = false;
        fileInput.style.display = 'none';
        
        // Label will automatically trigger fileInput when clicked (via for="fileInput")
        // But add explicit handler as backup
        uploadBtn.addEventListener('click', function(e) {
            if (!fileInput) {
                alert('File upload element not found. Please refresh the page.');
                return;
            }
            
            // Ensure file input is enabled
            fileInput.disabled = false;
            
            // If label's natural behavior doesn't work, trigger manually
            setTimeout(() => {
                if (fileInput) {
                    fileInput.click();
                }
            }, 0);
        });
        
        console.log('Upload button event listener attached');
        
        // File input change handler
        fileInput.addEventListener('change', function(e) {
            console.log('=== FILE INPUT CHANGED ===');
            console.log('Files:', e.target.files);
            console.log('File count:', e.target.files ? e.target.files.length : 0);
            
            if (e.target.files && e.target.files.length > 0) {
                const selectedFile = e.target.files[0];
                console.log('File selected:', {
                    name: selectedFile.name,
                    size: selectedFile.size,
                    type: selectedFile.type
                });
                console.log('Calling handleFileUpload...');
                handleFileUpload(e);
            } else {
                console.warn('No files selected - user may have cancelled');
            }
        });
        
        console.log('File input change listener attached');
        
        // Also allow direct click on upload area (but not on button)
        if (uploadArea) {
            uploadArea.addEventListener('click', function(e) {
                // Only trigger if clicking on the area itself, not on the button
                if (e.target === uploadArea || (e.target.closest && e.target.closest('#uploadContent') && e.target !== uploadBtn)) {
                    if (fileInput && !fileInput.disabled) {
                        fileInput.click();
                    }
                }
            });
        }
    } else {
        console.error('File upload elements not found. Required IDs: fileInput, uploadBtn');
        if (!fileInput) console.error('Missing: #fileInput');
        if (!uploadBtn) console.error('Missing: #uploadBtn');
    }

    // Drag and drop - check if upload area exists
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.style.borderColor = '#64B5F6';
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.style.borderColor = '#E0E0E0';
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.style.borderColor = '#E0E0E0';
            if (e.dataTransfer.files.length > 0 && fileInput) {
                fileInput.files = e.dataTransfer.files;
                handleFileUpload({ target: fileInput });
            }
        });
    }

    // Chat buttons - check if elements exist
    const submitBtn = document.getElementById('submitBtn');
    const endBtn = document.getElementById('endBtn');
    
    if (submitBtn) {
        submitBtn.addEventListener('click', submitAnswer);
    }
    if (endBtn) {
        endBtn.addEventListener('click', endInterview);
    }
}

async function loadProfile() {
    const content = document.getElementById('profileContent');
    if (!content) {
        console.warn('Profile content element not found');
        return;
    }

    // Ensure API_BASE is configured before making requests
    await ensureApiBaseReady();

    // Try to get user_id from multiple sources
    let userId = currentUserId || window.CURRENT_USER_ID;
    
    // If not in global variable, try storage
    if (!userId) {
        userId = localStorage.getItem('user_id') || sessionStorage.getItem('resume_user_id');
        if (userId) {
            currentUserId = userId;
            window.CURRENT_USER_ID = userId;
        }
    }

    // If still no user_id, try to get from API
    if (!userId) {
        try {
            const user = await getCurrentUser();
            if (user && user.user_id) {
                userId = user.user_id;
                currentUserId = userId;
                window.CURRENT_USER_ID = userId;
            }
        } catch (e) {
            console.log('Could not get current user:', e.message);
        }
    }

    // If we have a user_id, fetch the profile
    if (userId) {
        try {
            // Ensure API_BASE is set before making request
            const apiBase = getApiBase();
            const profileUrl = `${apiBase}/api/profile/${userId}`;
            
            // Make request with timeout and better error handling
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
            
            let res;
            try {
                res = await fetch(profileUrl, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    signal: controller.signal,
                    mode: 'cors', // Explicitly set CORS mode
                    credentials: 'omit' // Don't send credentials for CORS
                });
                clearTimeout(timeoutId);
            } catch (fetchError) {
                clearTimeout(timeoutId);
                
                // Handle different types of fetch errors
                if (fetchError.name === 'AbortError') {
                    throw new Error('Request timeout - server took too long to respond. Please check if the backend server is running.');
                } else if (fetchError.message.includes('Failed to fetch') || fetchError.message.includes('NetworkError')) {
                    throw new Error('Cannot connect to server. Please ensure the backend server is running and accessible. Check console for details.');
                } else {
                    throw new Error(`Network error: ${fetchError.message}`);
                }
            }
            
            
            if (res.status === 404) {
                content.innerHTML = '<p style="color: #666; padding: 20px; text-align: center;">No profile found. Upload a resume to create your profile.</p>';
                return;
            }
            
            if (!res.ok) {
                // Try to get error message from response
                let errorMessage = `Failed to load profile: ${res.status} ${res.statusText}`;
                try {
                    const errorData = await res.json();
                    errorMessage = errorData.detail || errorData.error || errorMessage;
                } catch (parseError) {
                    // Response might not be JSON - try to get text
                    try {
                        const errorText = await res.text();
                        if (errorText) {
                            errorMessage = errorText.substring(0, 200); // Limit length
                        }
                    } catch (textError) {
                        // Can't read response at all
                    }
                }
                console.error('[PROFILE] Error response:', errorMessage);
                throw new Error(errorMessage);
            }
            
            const profile = await res.json();
            displayProfile(profile);
            return;
        } catch (e) {
            console.error('[PROFILE] Error loading profile:', e);
            console.error('[PROFILE] Error name:', e.name);
            console.error('[PROFILE] Error message:', e.message);
            console.error('[PROFILE] Error stack:', e.stack);
            
            // Show more specific error message based on error type
            let errorMsg = e.message || 'Unknown error';
            
            // Provide helpful guidance based on error
            if (errorMsg.includes('timeout') || errorMsg.includes('too long')) {
                errorMsg = 'Server timeout. Please check if the backend server is running.';
            } else if (errorMsg.includes('Cannot connect') || errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
                errorMsg = 'Cannot connect to server. Please ensure the backend server is running at ' + getApiBase();
            } else if (errorMsg.includes('CORS')) {
                errorMsg = 'CORS error. Please check backend CORS configuration.';
            }
            
            content.innerHTML = `<p style="color: #999; padding: 20px; text-align: center;">Unable to load profile: ${errorMsg}. <br><small>Check browser console (F12) for more details.</small></p>`;
            return;
        }
    }

    // No user_id available - show message to upload resume
    content.innerHTML = '<p style="color: #666; padding: 20px; text-align: center;">No profile found yet. Upload your resume below to create your profile and get started!</p>';
}

function displayProfile(profile) {
    const skills = profile.skills || [];
    const skillsHtml = skills.length > 0
        ? skills.map(s => `<span class="skill-tag">${s}</span>`).join('')
        : '<p style="color: #999; font-size: 13px;">No skills yet. Upload your resume.</p>';

    document.getElementById('profileContent').innerHTML = `
        <div style="display: grid; gap: 15px;">
            <div><strong>Name:</strong> ${profile.name || 'Not set'}</div>
            <div><strong>Email:</strong> ${profile.email || 'Not set'}</div>
            <div><strong>Experience:</strong> ${profile.experience_level || 'Not set'}</div>
            <div>
                <strong>Skills:</strong>
                <div class="skills-list" style="margin-top: 8px;">${skillsHtml}</div>
            </div>
        </div>
    `;
}

async function handleFileUpload(e) {
    console.log('=== handleFileUpload CALLED ===');
    console.log('Event:', e);
    console.log('Event target:', e.target);
    console.log('Files:', e.target?.files);
    console.log('File count:', e.target?.files ? e.target.files.length : 0);
    
    const file = e.target?.files?.[0];
    if (!file) {
        console.warn('No file selected in handleFileUpload');
        return;
    }
    
    console.log('File found:', {
        name: file.name,
        size: file.size,
        type: file.type
    });

    // Validate file extension
    const fileName = file.name || '';
    const ext = '.' + fileName.split('.').pop().toLowerCase();
    if (!['.pdf', '.docx', '.doc'].includes(ext)) {
        alert('Please upload a PDF or DOCX file. Your file: ' + fileName);
        e.target.value = ''; // Reset file input
        return;
    }

    // Validate file size (2MB = 2 * 1024 * 1024 bytes)
    const maxSize = 2 * 1024 * 1024; // 2MB
    if (file.size > maxSize) {
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        alert(`File size (${fileSizeMB} MB) exceeds 2MB limit. Please upload a smaller file.`);
        e.target.value = ''; // Reset file input
        return;
    }

    // Show scanning state
    const uploadContent = document.getElementById('uploadContent');
    const uploadScanning = document.getElementById('uploadScanning');
    
    if (uploadContent) uploadContent.classList.add('hidden');
    if (uploadScanning) uploadScanning.classList.remove('hidden');

    // Get user ID from storage (backend generates it from resume name)
    // DO NOT generate UUID - backend creates stable user_id from name
    let userId = currentUserId || window.CURRENT_USER_ID || 
                 localStorage.getItem('user_id') || 
                 sessionStorage.getItem('resume_user_id');
    
    if (!userId) {
        console.warn('No user_id found in storage. Backend will generate one from resume name.');
        // Don't generate UUID - backend will create user_id from extracted name
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        // Backend now generates stable user_id from name - no need to pass user_id
        const uploadUrl = `${getApiBase()}/api/profile/upload-resume`;
        
        console.log('=== UPLOAD START ===');
        console.log('Upload URL:', uploadUrl);
        console.log('File:', fileName, 'Size:', file.size, 'bytes', 'Type:', file.type);
        console.log('FormData entries:', Array.from(formData.entries()).map(([k, v]) => [k, v instanceof File ? `${v.name} (${v.size} bytes)` : v]));
        
        const res = await fetch(uploadUrl, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header - browser will set it with boundary for FormData
        });
        
        console.log('Response received:', {
            status: res.status,
            statusText: res.statusText,
            ok: res.ok,
            contentType: res.headers.get('content-type')
        });

        // Read response as text first (can only read once)
        const responseText = await res.text();
        console.log('Response text length:', responseText.length);
        console.log('Response text (first 500 chars):', responseText.substring(0, 500));

        if (!res.ok) {
            console.error('Upload failed - Response text:', responseText);
            let errorData;
            try {
                errorData = JSON.parse(responseText);
                console.error('Parsed error data:', errorData);
            } catch (parseErr) {
                console.error('Failed to parse error response:', parseErr);
                errorData = { error: responseText || `Server error: ${res.status}` };
            }
            throw new Error(errorData.error || errorData.detail || `Upload failed: ${res.status} ${res.statusText}`);
        }

        // Parse JSON response
        let data;
        try {
            data = JSON.parse(responseText);
            console.log('Upload successful! Response data:', data);
            console.log('Session ID:', data.session_id);
        } catch (parseErr) {
            console.error('Failed to parse JSON response:', parseErr);
            console.error('Response text was:', responseText);
            throw new Error('Invalid response from server. Please try again.');
        }

        // Always redirect to analysis page, even on error
        const sessionId = data.session_id || data.sessionId || 'new';
        
        if (!sessionId || sessionId === 'new') {
            console.warn('No session_id in response, generating one');
            const fallbackSessionId = 'upload_' + Date.now();
            data.session_id = fallbackSessionId;
        }
        
        // Store analysis data in sessionStorage (including errors)
        sessionStorage.setItem('resume_analysis_data', JSON.stringify(data));
        sessionStorage.setItem('resume_analysis_session', sessionId);
        // Store stable user_id from backend response (generated from name)
        // Note: user_id may be null for error responses, which is OK
        const stableUserId = data.user_id;
        if (data.success === true && !stableUserId) {
            console.error('Backend did not return user_id in success response!', data);
            throw new Error('Backend did not return user_id. Please try uploading again.');
        }
        // For error responses, user_id can be null - don't throw
        
        // Store in both localStorage (persistent) and sessionStorage (session)
        // Only store user_id if it exists (not for error responses)
        if (stableUserId) {
            localStorage.setItem('user_id', stableUserId);
            sessionStorage.setItem('resume_user_id', stableUserId);
            
            // Update global user_id
            currentUserId = stableUserId;
            window.CURRENT_USER_ID = stableUserId;
        }
        
        console.log('Stored stable user_id from backend:', stableUserId);
        console.log('Saved to localStorage and sessionStorage');
        
        console.log('Stored in sessionStorage:', {
            session_id: sessionId,
            user_id: stableUserId,
            interview_session_id: data.interview_session_id,
            has_data: !!sessionStorage.getItem('resume_analysis_data')
        });
        
        console.log('Redirecting to resume-analysis.html?session=' + sessionId);
        // Redirect to resume analysis page (will show error state if failed)
        window.location.href = `resume-analysis.html?session=${sessionId}`;
    } catch (e) {
        console.error('=== UPLOAD ERROR ===');
        console.error('Error type:', e.constructor.name);
        console.error('Error message:', e.message);
        console.error('Error stack:', e.stack);
        
        // On network/parsing error, still redirect with error state
        const errorData = {
            success: false,
            error: e.message || 'Failed to upload resume. Please try again.',
            session_id: 'error_' + Date.now()
        };
        sessionStorage.setItem('resume_analysis_data', JSON.stringify(errorData));
        sessionStorage.setItem('resume_analysis_session', errorData.session_id);
        // Don't store invalid user_id - wait for successful upload
        // sessionStorage.setItem('resume_user_id', userId || 'unknown');
        
        console.log('Stored error in sessionStorage, redirecting...');
        window.location.href = `resume-analysis.html?session=${errorData.session_id}`;
    } finally {
        // Reset file input
        if (e.target) {
            e.target.value = '';
        }
        console.log('=== UPLOAD COMPLETE ===');
    }
}

async function startInterview(mode) {
    interviewMode = mode;
    currentQuestionNum = 0;
    document.getElementById('chatSection').classList.remove('hidden');
    
    // Start interview session
    try {
        const res = await fetch(`${getApiBase()}/api/interview/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId })
        });
        
        if (res.ok) {
            const data = await res.json();
            currentQuestionNum = data.question_number;
            totalQuestions = data.total_questions;
            
            window.currentQuestion = {
                id: 0,
                text: data.current_question.question,
                type: data.current_question.type
            };
            
            displayQuestion(data.current_question.question);
            updateProgress();
            
            if (interviewMode === 'timed') {
                startTimer();
            }
        }
    } catch (e) {
        console.error('Start interview error:', e);
        fetchNextQuestion();
    }
}

async function fetchNextQuestion() {
    if (!currentSessionId) return;

    try {
        const res = await fetch(`${getApiBase()}/api/interview/session/${currentSessionId}/next-question/${currentQuestionNum}`);
        
        if (res.status === 204 || res.status === 404) {
            endInterview(true);
            return;
        }

        const data = await res.json();
        
        if (!data.has_next) {
            endInterview(true);
            return;
        }

        currentQuestionNum = data.question_number;
        
        // Store question info for submission
        window.currentQuestion = {
            id: data.question_id,
            text: data.question,
            type: data.question_type || 'Technical'
        };

        displayQuestion(data.question);
        updateProgress();

        if (interviewMode === 'timed') {
            startTimer();
        }
    } catch (e) {
        console.error('Fetch question error:', e);
    }
}

function displayQuestion(question) {
    const container = document.getElementById('chatContainer');
    const div = document.createElement('div');
    div.className = 'chat-message bot';
    div.innerHTML = `<p><strong>Question ${currentQuestionNum}:</strong> ${question}</p>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function updateProgress() {
    document.getElementById('progressText').textContent = `Question ${currentQuestionNum} of ${totalQuestions}`;
}

function startTimer() {
    timeRemaining = 60;
    document.getElementById('timerDisplay').classList.remove('hidden');
    updateTimer();

    timerInterval = setInterval(() => {
        timeRemaining--;
        updateTimer();
        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            submitAnswer(true);
        }
    }, 1000);
}

function updateTimer() {
    const timer = document.getElementById('timerDisplay');
    timer.textContent = `${timeRemaining}s`;
    if (timeRemaining <= 10) {
        timer.style.background = '#EF5350';
    }
}

async function submitAnswer(timeout = false) {
    const input = document.getElementById('answerInput');
    const answer = timeout ? '[Time expired]' : input.value.trim();

    if (!answer && !timeout) {
        alert('Please enter an answer.');
        return;
    }

    // Add user answer to chat
    const container = document.getElementById('chatContainer');
    const div = document.createElement('div');
    div.className = 'chat-message';
    div.innerHTML = `<p><strong>You:</strong> ${answer}</p>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    input.value = '';
    input.disabled = true;
    document.getElementById('submitBtn').disabled = true;

    try {
        const currentQuestion = window.currentQuestion || { id: 0, text: '', type: 'Technical' };
        
        const res = await fetch(`${getApiBase()}/api/interview/submit-answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                question_id: currentQuestion.id || 0,
                question_number: currentQuestionNum,
                question_text: currentQuestion.text || '',
                question_type: currentQuestion.type || 'Technical',
                user_answer: answer,
                response_time: timeout ? 60 : null
            })
        });

        const data = await res.json();
        
        // Show scores
        const scoreDiv = document.createElement('div');
        scoreDiv.className = 'chat-message bot';
        scoreDiv.innerHTML = `
            <p><strong>Score:</strong> ${data.scores.overall}/100</p>
            <p style="font-size: 13px; color: #666; margin-top: 5px;">${data.scores.feedback}</p>
        `;
        container.appendChild(scoreDiv);

        // Next question
        setTimeout(() => {
            fetchNextQuestion();
            input.disabled = false;
            document.getElementById('submitBtn').disabled = false;
            if (timerInterval) {
                clearInterval(timerInterval);
                document.getElementById('timerDisplay').classList.add('hidden');
            }
        }, 1500);
    } catch (e) {
        console.error('Submit error:', e);
        input.disabled = false;
        document.getElementById('submitBtn').disabled = false;
    }
}

function endInterview(completed = false) {
    if (timerInterval) {
        clearInterval(timerInterval);
    }

    document.getElementById('chatSection').classList.add('hidden');
    document.getElementById('chatContainer').innerHTML = '';
    document.getElementById('answerInput').value = '';

    if (completed) {
        alert('Interview completed!');
        loadDashboard();
    }
}

async function loadDashboard() {
    if (!currentUserId) {
        // Try to get user, but don't fail if not found
        const user = await getCurrentUser();
        if (!user || !currentUserId) {
            // No user found - this is OK, don't show error
            return;
        }
    }
    const userId = currentUserId;

    try {
        const res = await fetch(`${getApiBase()}/api/dashboard/performance/${userId}`);
        const data = await res.json();

        // Update Total Interviews
        const totalInterviews = data.total_interviews || 0;
        document.getElementById('totalInterviews').textContent = totalInterviews;
        
        // Update Average Score with progress bar
        const avgScore = Math.round(data.average_score || 0);
        document.getElementById('avgScore').textContent = avgScore;
        const avgScorePercent = Math.min(avgScore, 100);
        document.getElementById('avgScoreFill').style.width = `${avgScorePercent}%`;
        document.getElementById('avgScoreText').textContent = `${avgScorePercent}%`;
        
        // Update Completion Rate with progress bar
        const completionRate = data.completion_rate || 0;
        const completionPercent = Math.round(completionRate);
        document.getElementById('completionRate').textContent = `${completionPercent}%`;
        document.getElementById('completionFill').style.width = `${completionPercent}%`;

        // Update Skills
        const strong = data.skill_analysis?.strong_skills || [];
        const weak = data.skill_analysis?.weak_areas || [];

        document.getElementById('strongSkillsCount').textContent = strong.length;
        document.getElementById('strongSkills').innerHTML = strong.length > 0
            ? strong.map(s => `<span class="skill-tag">${s}</span>`).join('')
            : '<p style="color: #999; font-size: 13px; padding: 10px;">No data yet. Complete interviews to see your strengths!</p>';

        document.getElementById('weakSkillsCount').textContent = weak.length;
        document.getElementById('weakSkills').innerHTML = weak.length > 0
            ? weak.map(s => `<span class="skill-tag">${s}</span>`).join('')
            : '<p style="color: #999; font-size: 13px; padding: 10px;">No data yet. Complete interviews to identify areas for improvement!</p>';

        // Update Recent Interviews with better formatting
        const interviews = data.recent_interviews || [];
        const list = document.getElementById('pastInterviews');
        if (interviews.length > 0) {
            list.innerHTML = interviews.map(i => {
                const date = new Date(i.completed_at);
                const formattedDate = date.toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric', 
                    year: 'numeric' 
                });
                const score = Math.round(i.overall_score || 0);
                return `
                    <div class="interview-item">
                        <div class="interview-item-info">
                            <div class="interview-item-role">${i.role || 'Interview'}</div>
                            <div class="interview-item-meta">
                                <span>${i.experience_level || 'N/A'}</span>
                                <span>•</span>
                                <span>${i.answered_questions || 0}/${i.total_questions || 0} questions</span>
                                <span>•</span>
                                <span>${formattedDate}</span>
                            </div>
                        </div>
                        <div class="interview-item-score">
                            <span class="score-badge">${score}</span>
                            <span>/100</span>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            list.innerHTML = '<p style="color: #999; text-align: center; padding: 30px; font-size: 14px;">No interviews yet. Start practicing to see your progress here!</p>';
        }
    } catch (e) {
        console.error('Dashboard load error:', e);
        // Show error message
        document.getElementById('totalInterviews').textContent = '—';
        document.getElementById('avgScore').textContent = '—';
        document.getElementById('completionRate').textContent = '—';
    }
}

