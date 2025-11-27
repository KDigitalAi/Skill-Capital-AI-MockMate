/**
 * Technical Interview - Frontend JavaScript
 * Handles voice recording, audio playback, and interview flow
 * 
 * NOTE: This file requires api-config.js to be loaded first
 * api-config.js provides: getApiBase(), ensureApiBaseReady(), API_BASE
 */

// State
let currentUserId = null;
let interviewSessionId = null;
let conversationHistory = [];
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let currentQuestion = null;
let interviewActive = false;

// Get current authenticated user from user_profiles
async function getCurrentUser() {
    try {
        // First, try to get from localStorage (persistent) or sessionStorage
        const storedUserId = localStorage.getItem('user_id') || 
                            sessionStorage.getItem('resume_user_id') || 
                            window.CURRENT_USER_ID;
        if (storedUserId) {
            currentUserId = storedUserId;
            window.CURRENT_USER_ID = storedUserId;
            return { user_id: storedUserId };
        }
        
        // If not in storage, fetch from API
        const res = await fetch(`${getApiBase()}/api/profile/current`);
        if (!res.ok) {
            throw new Error(`Failed to get current user: ${res.status}`);
        }
        const user = await res.json();
        currentUserId = user.user_id;
        
        // Store in both localStorage (persistent) and sessionStorage
        if (currentUserId) {
            localStorage.setItem('user_id', currentUserId);
            sessionStorage.setItem('resume_user_id', currentUserId);
            window.CURRENT_USER_ID = currentUserId;
        }
        
        return user;
    } catch (e) {
        console.error('Error getting current user:', e);
        // Try one more fallback: check storage
        const fallbackUserId = localStorage.getItem('user_id') || 
                               sessionStorage.getItem('resume_user_id') || 
                               window.CURRENT_USER_ID;
        if (fallbackUserId) {
            currentUserId = fallbackUserId;
            window.CURRENT_USER_ID = fallbackUserId;
            return { user_id: fallbackUserId };
        }
        throw new Error('No authenticated user found. Please ensure you have uploaded a resume and have a valid user profile.');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
    try {
        // Get current user first
        await getCurrentUser();
        
        // Setup event listeners
        setupEventListeners();
    } catch (e) {
        console.error('Initialization failed:', e);
        alert(`Error: ${e.message}`);
    }
}

function setupEventListeners() {
    document.getElementById('startInterviewBtn').addEventListener('click', startInterview);
    document.getElementById('endInterviewBtn').addEventListener('click', endInterview);
    document.getElementById('voiceButton').addEventListener('click', toggleRecording);
    document.getElementById('restartInterviewBtn').addEventListener('click', () => {
        window.location.reload();
    });
}

async function startInterview() {
    // Ensure we have current user
    if (!currentUserId) {
        await getCurrentUser();
    }
    
    // Validate userId is available
    if (!currentUserId) {
        throw new Error('userId is not defined. Please ensure you have uploaded a resume and have a valid user profile.');
    }
    
    const userId = currentUserId;
    
    
    // Show loading
    document.getElementById('setupSection').classList.add('hidden');
    document.getElementById('interviewSection').classList.remove('hidden');
    document.getElementById('loadingMessage').classList.remove('hidden');
    document.getElementById('interviewStatus').textContent = 'Starting Interview...';
    document.getElementById('interviewStatus').classList.add('active');
    
    // Clear conversation container
    const container = document.getElementById('conversationContainer');
    container.innerHTML = '<div class="loading" id="loadingMessage">Initializing interview...</div>';

    try {
        // Start technical interview session
        // Use correct endpoint: /api/interview/technical/start
        const response = await fetch(`${getApiBase()}/api/interview/technical/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });

        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[INTERVIEW] Error response:', errorText);
            throw new Error(`Failed to start interview: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        
        interviewSessionId = data.session_id;
        interviewActive = true;
        conversationHistory = data.conversation_history || [];

        // IMPORTANT: Once we have a session ID, keep interview section visible
        // Don't hide it even if getting questions fails
        document.getElementById('setupSection').classList.add('hidden');
        document.getElementById('interviewSection').classList.remove('hidden');

        // Update status
        document.getElementById('interviewStatus').textContent = 'Interview Active';
        document.getElementById('interviewStatus').classList.add('active');
        
        // Clear loading message
        const loadingMsg = document.getElementById('loadingMessage');
        if (loadingMsg) {
            loadingMsg.classList.add('hidden');
        }
        
        // Clear container and prepare for messages
        container.innerHTML = '';

        // Display conversation history if any
        if (conversationHistory.length > 0) {
            conversationHistory.forEach(msg => {
                displayMessage(msg.role, msg.content, msg.audio_url);
            });
        }

        // Get first question from AI
        // If this fails, show error but keep interview section visible
        try {
            await getNextQuestion();
        } catch (questionError) {
            console.error('[INTERVIEW] Error getting first question:', questionError);
            showError(`Failed to get first question: ${questionError.message || 'Please try again.'}`);
            document.getElementById('voiceStatus').textContent = 'Error loading question. The interview session is active - you can try again.';
            // Keep interview section visible - don't redirect
        }

    } catch (error) {
        console.error('[INTERVIEW] Start interview error:', error);
        const errorMsg = error.message || 'Failed to start interview. Please try again.';
        
        // Show alert to user instead of silently hiding
        alert(`Failed to start interview: ${errorMsg}\n\nPlease ensure you have uploaded a resume and try again.`);
        
        // Keep interview section visible but show error
        const container = document.getElementById('conversationContainer');
        if (container) {
            container.innerHTML = `<div class="error-message">${errorMsg}<br><br>Please check your resume upload and try again.</div>`;
        }
        
        // Show setup section again so user can retry
        document.getElementById('setupSection').classList.remove('hidden');
        document.getElementById('interviewSection').classList.add('hidden');
        document.getElementById('interviewStatus').textContent = 'Ready to Start';
        document.getElementById('interviewStatus').classList.remove('active');
        
        // Reset interview state
        interviewActive = false;
        interviewSessionId = null;
    }
}

async function getNextQuestion() {
    if (!interviewSessionId) {
        console.error('[INTERVIEW] No session ID available');
        showError('No interview session found. Please start the interview again.');
        // Don't redirect - just show error and let user retry
        return;
    }

    try {
        
        // Hide loading message if still visible
        const loadingMsg = document.getElementById('loadingMessage');
        if (loadingMsg) {
            loadingMsg.classList.add('hidden');
        }
        
        // Get next question from AI
        const response = await fetch(`${getApiBase()}/api/interview/technical/${interviewSessionId}/next-question`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[INTERVIEW] Error getting question:', errorText);
            throw new Error(`Failed to get next question: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        
        if (data.interview_completed) {
            // Interview is complete
            await completeInterview();
            return;
        }

        if (!data.question) {
            throw new Error('No question received from server');
        }

        currentQuestion = data.question;
        conversationHistory.push({
            role: 'ai',
            content: data.question,
            audio_url: data.audio_url
        });

        // Display question
        displayMessage('ai', data.question, data.audio_url);

        // Play audio if available
        if (data.audio_url) {
            playAudio(data.audio_url);
        }

        // Update status
        document.getElementById('voiceStatus').textContent = 'Click the microphone to record your answer';
        document.getElementById('voiceButton').classList.remove('listening');

    } catch (error) {
        console.error('[INTERVIEW] Get question error:', error);
        const errorMsg = `Failed to get question: ${error.message || 'Please try again.'}`;
        showError(errorMsg);
        
        // Show alert for critical errors
        if (error.message && error.message.includes('500')) {
            alert(`Interview error: ${errorMsg}\n\nThe interview session may have encountered an issue. You can try starting a new interview.`);
        }
        
        // Keep interview section visible - don't redirect
        document.getElementById('voiceStatus').textContent = 'Error occurred. Please try recording again or start a new interview.';
    }
}

async function toggleRecording() {
    if (!interviewActive) return;

    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await processAudioAnswer(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        document.getElementById('voiceButton').classList.add('recording');
        document.getElementById('voiceStatus').textContent = 'Recording... Click again to stop';
    } catch (error) {
        console.error('Error accessing microphone:', error);
        const errorMsg = 'Microphone access denied. Please allow microphone access and try again.';
        showError(errorMsg);
        // Show alert but don't redirect
        alert(errorMsg);
        // Keep interview section visible
        document.getElementById('voiceStatus').textContent = 'Microphone access required. Please allow access and try again.';
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById('voiceButton').classList.remove('recording');
        document.getElementById('voiceStatus').textContent = 'Processing your answer...';
    }
}

async function processAudioAnswer(audioBlob) {
    try {
        // Convert audio to text using speech-to-text endpoint
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        const sttResponse = await fetch(`${getApiBase()}/api/interview/speech-to-text`, {
            method: 'POST',
            body: formData
        });

        if (!sttResponse.ok) {
            throw new Error('Failed to convert speech to text');
        }

        const sttData = await sttResponse.json();
        const userAnswer = sttData.text;

        // Display user's answer
        displayMessage('user', userAnswer);

        // Submit answer to backend
        await submitAnswer(userAnswer);

    } catch (error) {
        console.error('Process audio error:', error);
        const errorMsg = 'Failed to process your answer. Please try again.';
        showError(errorMsg);
        document.getElementById('voiceStatus').textContent = 'Error processing answer. Click the microphone to try again.';
        // Don't redirect - keep interview active
    }
}

async function submitAnswer(answer) {
    if (!interviewSessionId || !currentQuestion) return;

    try {
        console.log('[SUBMIT ANSWER] Submitting answer to backend...');
        const response = await fetch(`${getApiBase()}/api/interview/technical/${interviewSessionId}/submit-answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: currentQuestion,
                answer: answer
            })
        });

        if (!response.ok) {
            // CRITICAL FIX: Get error details from backend
            let errorDetail = 'Failed to submit answer';
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorData.message || errorDetail;
            } catch (e) {
                const errorText = await response.text();
                errorDetail = errorText || errorDetail;
            }
            console.error('[SUBMIT ANSWER] Backend error:', response.status, errorDetail);
            throw new Error(`Failed to submit answer: ${errorDetail}`);
        }

        const data = await response.json();
        
        // CRITICAL FIX: Validate response has expected data
        if (!data) {
            throw new Error('Empty response from server. Answer may not have been saved.');
        }
        
        console.log('[SUBMIT ANSWER] Answer submitted successfully');
        
        // Update conversation history
        conversationHistory.push({
            role: 'user',
            content: answer
        });

        // Display AI response if any
        if (data.ai_response) {
            conversationHistory.push({
                role: 'ai',
                content: data.ai_response,
                audio_url: data.audio_url
            });
            displayMessage('ai', data.ai_response, data.audio_url);
            
            if (data.audio_url) {
                playAudio(data.audio_url);
            }
        }

        // Check if interview is complete
        if (data.interview_completed) {
            await completeInterview();
        } else {
            // Get next question after a short delay
            setTimeout(() => {
                getNextQuestion();
            }, 2000);
        }

        document.getElementById('voiceStatus').textContent = 'Click the microphone to record your answer';

    } catch (error) {
        console.error('[SUBMIT ANSWER] Submit answer error:', error);
        const errorMsg = error.message || 'Failed to submit answer. Please try again.';
        showError(errorMsg);
        alert(`Error: ${errorMsg}\n\nYour answer may not have been saved. Please try recording again.`);
        document.getElementById('voiceStatus').textContent = 'Error submitting answer. Click the microphone to try again.';
        // Don't redirect - keep interview active
    }
}

async function completeInterview() {
    interviewActive = false;
    document.getElementById('interviewStatus').textContent = 'Interview Completed';
    document.getElementById('interviewStatus').classList.remove('active');
    document.getElementById('interviewStatus').classList.add('completed');
    document.getElementById('interviewSection').classList.add('hidden');
    document.getElementById('feedbackSection').classList.remove('hidden');

    // Generate feedback
    await generateFeedback();
}

async function generateFeedback() {
    if (!interviewSessionId) return;

    try {
        console.log('[FEEDBACK] Requesting feedback from backend...');
        const response = await fetch(`${getApiBase()}/api/interview/technical/${interviewSessionId}/feedback`, {
            method: 'GET'
        });

        if (!response.ok) {
            // CRITICAL FIX: Get error details from backend
            let errorDetail = 'Failed to generate feedback';
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorData.message || errorDetail;
            } catch (e) {
                const errorText = await response.text();
                errorDetail = errorText || errorDetail;
            }
            console.error('[FEEDBACK] Backend error:', response.status, errorDetail);
            throw new Error(errorDetail);
        }

        const feedback = await response.json();

        // CRITICAL FIX: Validate feedback data exists
        if (!feedback) {
            throw new Error('Empty feedback response from server');
        }

        console.log('[FEEDBACK] Feedback received successfully');

        // Display feedback
        document.getElementById('overallScore').textContent = Math.round(feedback.overall_score || 0);
        
        const strengthsList = document.getElementById('strengthsList');
        strengthsList.innerHTML = (feedback.strengths || []).map(s => `<li>${s}</li>`).join('');

        const improvementsList = document.getElementById('improvementsList');
        improvementsList.innerHTML = (feedback.areas_for_improvement || []).map(a => `<li>${a}</li>`).join('');

        const recommendationsList = document.getElementById('recommendationsList');
        recommendationsList.innerHTML = (feedback.recommendations || []).map(r => `<li>${r}</li>`).join('');

        document.getElementById('feedbackSummary').textContent = feedback.feedback_summary || 'No summary available.';

        document.getElementById('feedbackLoading').classList.add('hidden');
        document.getElementById('feedbackContent').classList.remove('hidden');

    } catch (error) {
        console.error('[FEEDBACK] Generate feedback error:', error);
        const errorMsg = error.message || 'Failed to generate feedback.';
        document.getElementById('feedbackLoading').innerHTML = `<div class="error-message">${errorMsg}<br><br>This may happen if answers were not saved properly. Please check the backend logs.</div>`;
    }
}

function displayMessage(role, content, audioUrl = null) {
    const container = document.getElementById('conversationContainer');
    if (!container) {
        console.error('[INTERVIEW] Conversation container not found');
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const header = role === 'ai' ? 'AI Interviewer' : 'You';
    messageDiv.innerHTML = `
        <div class="message-header">${header}</div>
        <div class="message-content">${content}</div>
        ${audioUrl ? `<audio class="audio-player" controls src="${audioUrl}"></audio>` : ''}
    `;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    
}

async function playAudio(audioUrl, retryCount = 0) {
    const MAX_RETRIES = 2;
    if (!audioUrl) {
        console.warn('[TTS] No audio URL provided');
        return;
    }
    
    try {
        // Construct full URL if relative
        let fullUrl = audioUrl.startsWith('http') ? audioUrl : `${getApiBase()}${audioUrl}`;
        
        // If URL contains text parameter, we need to fetch it via POST instead
        if (fullUrl.includes('text=')) {
            try {
                const url = new URL(fullUrl);
                const textParam = url.searchParams.get('text');
                if (textParam) {
                    const text = decodeURIComponent(textParam);
                    
                    // Use POST endpoint instead
                    const response = await fetch(`${getApiBase()}/api/interview/text-to-speech`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ text: text.trim() })
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`TTS failed: ${response.status} - ${errorText}`);
                    }
                    
                    const audioBlob = await response.blob();
                    if (audioBlob.size === 0) {
                        throw new Error('Empty audio blob received');
                    }
                    
                    fullUrl = URL.createObjectURL(audioBlob);
                }
            } catch (e) {
                console.warn('[TTS] Could not extract text from URL, trying direct playback:', e);
            }
        }
        
        const audio = new Audio(fullUrl);
        
        // Set up event handlers
        audio.onerror = (error) => {
            console.error('[TTS] Audio playback error:', error);
            if (fullUrl.startsWith('blob:')) {
                URL.revokeObjectURL(fullUrl);
            }
            
            // Retry on error
            if (retryCount < MAX_RETRIES) {
                setTimeout(() => playAudio(audioUrl, retryCount + 1), 1000 * (retryCount + 1));
            }
        };
        
        audio.onended = () => {
            if (fullUrl.startsWith('blob:')) {
                URL.revokeObjectURL(fullUrl);
            }
        };
        
        await audio.play();
        
    } catch (error) {
        console.error('[TTS] Error playing audio:', error);
        
        // Retry on network/loading errors
        if (retryCount < MAX_RETRIES && (error.message.includes('fetch') || error.message.includes('network') || error.message.includes('Failed to load'))) {
            setTimeout(() => playAudio(audioUrl, retryCount + 1), 1000 * (retryCount + 1));
        }
    }
}

function showError(message) {
    const container = document.getElementById('conversationContainer');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    container.appendChild(errorDiv);
    container.scrollTop = container.scrollHeight;
}

async function endInterview() {
    if (confirm('Are you sure you want to end the interview? Your progress will be saved.')) {
        interviewActive = false;
        
        if (isRecording) {
            stopRecording();
        }

        if (interviewSessionId) {
            try {
                await fetch(`${getApiBase()}/api/interview/technical/${interviewSessionId}/end`, {
                    method: 'POST'
                });
            } catch (error) {
                console.error('Error ending interview:', error);
            }
        }

        await completeInterview();
    }
}

