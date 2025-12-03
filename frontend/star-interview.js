/**
 * STAR Interview - Frontend JavaScript
 * Handles voice recording, audio playback, and interview flow
 * 
 * NOTE: This file requires api-config.js to be loaded first
 * api-config.js provides: getApiBase(), ensureApiBaseReady(), API_BASE
 * 
 * VERSION: 2.0 - Custom Modal Implementation (STAR End Interview)
 */
console.log('[STAR INTERVIEW] Script loaded - Version 2.0 with Custom Modal');

// State
let currentUserId = null;
let interviewSessionId = null;
let conversationHistory = [];
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let currentQuestion = null;
let interviewActive = false;
let currentAudio = null; // Track current audio playback to prevent overlap
let isAudioPlaying = false; // Track if audio is currently playing
let starAudioQueue = []; // Queue for STAR interview audio (follow-up → question sequence)

// Simple FIFO queue for STAR interview audio to ensure sequential playback
function enqueueAudio(textOrUrl) {
    if (!textOrUrl) {
        return;
    }
    console.log('[STAR INTERVIEW TTS] Enqueue audio:', String(textOrUrl).substring(0, 80) + '...');
    starAudioQueue.push(textOrUrl);

    // If nothing is currently playing, start immediately
    if (!isAudioPlaying) {
        playNextFromStarQueue();
    }
}

function playNextFromStarQueue() {
    if (isAudioPlaying) {
        // Current audio still playing; wait for onended/onerror to advance the queue
        return;
    }
    if (starAudioQueue.length === 0) {
        return;
    }

    const next = starAudioQueue.shift();
    console.log('[STAR INTERVIEW TTS] Dequeue and play next audio:', String(next).substring(0, 80) + '...');
    // Fire-and-forget; playAudio will manage onended/onerror and may call playNextFromStarQueue again
    playAudio(next).catch(err => {
        console.warn('[STAR INTERVIEW TTS] Queue item playback failed:', err);
        // Move on to the next item to avoid getting stuck
        setTimeout(() => playNextFromStarQueue(), 100);
    });
}

// Loading state management to prevent double submission
let isLoading = {
    startInterview: false,
    submitAnswer: false,
    getNextQuestion: false,
    generateFeedback: false,
    playAudio: false
};

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
    // Prevent double submission
    if (isLoading.startInterview) {
        return;
    }
    
    try {
        setLoadingState('startInterview', true);
        
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
        // Start STAR interview session
        // Use endpoint: /api/interview/star/start
        const response = await fetch(`${getApiBase()}/api/interview/star/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });

        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[STAR INTERVIEW] Error response:', errorText);
            throw new Error(`Failed to start interview: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        
        interviewSessionId = data.session_id;
        interviewActive = true;
        conversationHistory = [];

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

        // Display first question if available
        if (data.question) {
            currentQuestion = data.question;
            conversationHistory.push({
                role: 'ai',
                content: data.question,
                audio_url: data.audio_url
            });
            // Display question with audio URL (same as technical interview)
            displayMessage('ai', data.question, data.audio_url);
            
            // Play audio if available (same as technical interview)
            // Note: playAudio is called after user interaction (button click), so autoplay should work
            if (data.audio_url) {
                console.log('[STAR INTERVIEW] ✅ audio_url found, enqueueing audio:', data.audio_url);
                // Use setTimeout to ensure this runs after UI update but still right after user interaction
                setTimeout(() => {
                    enqueueAudio(data.audio_url);
                }, 100);
            } else {
                console.error('[STAR INTERVIEW] ❌ No audio_url received for first question. Response keys:', Object.keys(data));
                document.getElementById('voiceStatus').textContent = 'Click the microphone to record your answer';
            }
        } else {
            showError('No question received. Please try again.');
        }

    } catch (error) {
            // Create error object with status if available
            const errorObj = {
                message: error.message || 'Failed to start interview. Please try again.',
                status: error.status || (error.response?.status),
                response: error.response,
                originalError: error
            };
            
            showUserFriendlyError(errorObj, 'startInterview', true);
        
        // Show setup section again so user can retry
        document.getElementById('setupSection').classList.remove('hidden');
        document.getElementById('interviewSection').classList.add('hidden');
        document.getElementById('interviewStatus').textContent = 'Ready to Start';
        document.getElementById('interviewStatus').classList.remove('active');
        
        // Reset interview state
        interviewActive = false;
        interviewSessionId = null;
        }
    } catch (error) {
        // Outer catch for unexpected errors
        const errorObj = {
            message: error.message || 'An unexpected error occurred.',
            originalError: error
        };
        showUserFriendlyError(errorObj, 'startInterview', true);
    } finally {
        // Always re-enable button and hide loading states
        setLoadingState('startInterview', false);
        const loadingMsg = document.getElementById('loadingMessage');
        if (loadingMsg) {
            loadingMsg.classList.add('hidden');
        }
    }
}

async function toggleRecording() {
    if (!interviewActive) return;
    
    // Prevent recording while audio is playing (same as technical interview behavior)
    if (isAudioPlaying) {
        console.log('[STAR INTERVIEW] Cannot record while audio is playing');
        document.getElementById('voiceStatus').textContent = 'Please wait for the question to finish...';
        return;
    }

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

/**
 * Detect if STT result should be classified as "No Answer"
 * Returns {isNoAnswer: boolean, reason: string} if it's a no-answer case
 */
function detectNoAnswer(sttText) {
    if (!sttText || !sttText.trim()) {
        return { isNoAnswer: true, reason: 'empty_or_whitespace' };
    }
    
    const trimmed = sttText.trim();
    const upper = trimmed.toUpperCase();
    
    // List of known garbage phrases (case-insensitive)
    const garbagePhrases = [
        'THANK YOU',
        'THANKS',
        'THANK YOU FOR WATCHING',
        'SHOWCASING VIDEO',
        'THANKS FOR WATCHING',
        'THANK YOU FOR WATCHING THIS VIDEO',
        'THANKS FOR WATCHING THIS',
        'THANK YOU FOR WATCHING!',
        'THANKS FOR WATCHING!'
    ];
    
    // Check for exact garbage phrase matches
    for (const phrase of garbagePhrases) {
        if (upper === phrase || upper.startsWith(phrase + ' ') || upper.endsWith(' ' + phrase)) {
            return { isNoAnswer: true, reason: `garbage_phrase: ${trimmed}` };
        }
    }
    
    // Check for single-word fillers with no semantic content
    const words = trimmed.split(/\s+/);
    if (words.length === 1) {
        const singleWord = upper;
        // Common single-word fillers that indicate no real answer
        const fillerWords = ['UM', 'UH', 'ER', 'AH', 'OH', 'WELL', 'SO', 'LIKE', 'YEAH', 'YEP', 'NOPE', 'OK', 'OKAY', 'SURE'];
        if (fillerWords.includes(singleWord)) {
            return { isNoAnswer: true, reason: `single_word_filler: ${trimmed}` };
        }
    }
    
    // Very short responses (less than 3 characters) are likely not real answers
    if (trimmed.length < 3) {
        return { isNoAnswer: true, reason: `too_short: ${trimmed}` };
    }
    
    // ✅ FIX: Detect hallucinated/irrelevant answers that are clearly not interview responses
    // These are answers that don't relate to interview questions at all
    const hallucinatedPatterns = [
        /see you in the car/i,
        /take care of yourself/i,
        /look after yourself/i,
        /see you later/i,
        /goodbye/i,
        /farewell/i,
        /see you soon/i,
        /have a good day/i,
        /have a nice day/i,
        /take care/i,
        /bye/i,
        /good night/i,
        /good morning/i,
        /good afternoon/i,
        /thanks for watching/i,
        /thank you for watching/i,
        /showcasing video/i,
        /end of video/i,
        /video ended/i,
        /recording ended/i,
        /test test/i,
        /testing testing/i,
        /one two three/i,
        /hello hello/i,
        /can you hear me/i,
        /is this working/i,
        /microphone test/i
    ];
    
    // Check if answer matches any hallucinated pattern
    for (const pattern of hallucinatedPatterns) {
        if (pattern.test(trimmed)) {
            return { isNoAnswer: true, reason: `hallucinated_pattern: ${trimmed}` };
        }
    }
    
    // ✅ FIX: Detect URLs, website references, and other clearly irrelevant text
    // Check for URL patterns (www., http://, https://, .com, .co.uk, .org, etc.)
    const urlPatterns = [
        /www\./i,
        /http:\/\//i,
        /https:\/\//i,
        /\.com/i,
        /\.co\.uk/i,
        /\.org/i,
        /\.net/i,
        /\.io/i,
        /\.edu/i,
        /\.gov/i,
        /subs by/i,
        /subtitle/i,
        /caption/i
    ];
    
    for (const pattern of urlPatterns) {
        if (pattern.test(trimmed)) {
            return { isNoAnswer: true, reason: `url_or_website_reference: ${trimmed}` };
        }
    }
    
    // ✅ FIX: Detect answers that are clearly not related to interview context
    // If answer contains phrases that suggest it's not an interview answer
    const irrelevantPhrases = [
        'see you',
        'take care',
        'goodbye',
        'farewell',
        'bye',
        'later',
        'watching',
        'video',
        'recording',
        'test',
        'testing',
        'microphone',
        'can you hear',
        'is this working',
        'subs by',
        'subtitle',
        'caption',
        'www',
        'website',
        'url'
    ];
    
    const lowerTrimmed = trimmed.toLowerCase();
    // If answer contains multiple irrelevant phrases, it's likely hallucinated
    let irrelevantCount = 0;
    for (const phrase of irrelevantPhrases) {
        if (lowerTrimmed.includes(phrase)) {
            irrelevantCount++;
        }
    }
    
    // If answer contains 2+ irrelevant phrases, classify as "No Answer"
    if (irrelevantCount >= 2) {
        return { isNoAnswer: true, reason: `multiple_irrelevant_phrases: ${trimmed}` };
    }
    
    // ✅ FIX: STRICT RULE - Detect parenthetical descriptions FIRST (highest priority)
    // These are clearly not interview answers - they describe background audio
    // Check for various parenthetical patterns - if text contains (* or *) or starts with ( or *
    if (trimmed.startsWith('(*') || 
        trimmed.startsWith('(') || 
        trimmed.startsWith('*') ||
        trimmed.includes('(*') || 
        trimmed.includes('*)') ||
        trimmed.includes('( *') ||
        trimmed.includes('* )') ||
        (trimmed.startsWith('*') && trimmed.endsWith('*')) ||
        /^\([^)]*[Ss]ong|[Mm]usic|[Ss]ound|[Aa]udio|[Pp]laying[^)]*\)/i.test(trimmed) ||
        /\([^)]*[Ss]ong|[Mm]usic|[Ss]ound|[Aa]udio|[Pp]laying[^)]*\)/i.test(trimmed)) {
        return { isNoAnswer: true, reason: `parenthetical_description: ${trimmed}` };
    }
    
    // ✅ FIX: Detect single irrelevant phrase if it's clearly not an answer
    // If answer contains "subs by" or similar, it's definitely not an interview answer
    if (lowerTrimmed.includes('subs by') || lowerTrimmed.includes('subtitle') || lowerTrimmed.includes('caption')) {
        return { isNoAnswer: true, reason: `subtitle_or_caption_text: ${trimmed}` };
    }
    
    // ✅ FIX: Detect answers that describe what's happening rather than answering the question
    // If text contains words that describe actions/events rather than personal information
    const descriptivePhrases = [
        'playing',
        'song',
        'music',
        'sound',
        'audio',
        'noise',
        'background',
        'effect',
        'twinkle',
        'peel'
    ];
    
    let descriptiveCount = 0;
    for (const phrase of descriptivePhrases) {
        if (lowerTrimmed.includes(phrase)) {
            descriptiveCount++;
        }
    }
    
    // If answer contains 2+ descriptive phrases about audio/music, it's not an interview answer
    if (descriptiveCount >= 2) {
        return { isNoAnswer: true, reason: `audio_description_text: ${trimmed}` };
    }
    
    // ✅ FIX: STRICT RULE - Detect answers that are clearly describing background content
    // If answer contains "playing" + any music/song reference, it's describing audio, not answering
    // Also check for positional patterns (starts/ends with "playing") and specific phrases
    if (lowerTrimmed.includes('background music') || lowerTrimmed.includes('background sound')) {
        return { isNoAnswer: true, reason: `background_audio_description: ${trimmed}` };
    }
    
    // Check for "playing" combined with music/audio words, or positional patterns
    if (lowerTrimmed.includes('playing') && 
        (lowerTrimmed.includes('song') || lowerTrimmed.includes('music') || 
         lowerTrimmed.includes('sound') || lowerTrimmed.includes('audio'))) {
        return { isNoAnswer: true, reason: `background_audio_description: ${trimmed}` };
    }
    
    // Check for text that ends with "playing" or starts with "playing" (describing audio)
    if (lowerTrimmed.endsWith(' playing') || lowerTrimmed.startsWith('playing ')) {
        return { isNoAnswer: true, reason: `background_audio_description: ${trimmed}` };
    }
    
    // ✅ FIX: STRICT RULE - If answer contains song title patterns, it's not an interview answer
    // Common patterns: "twinkle", "star", "peel" (from song titles), etc.
    if (lowerTrimmed.includes('twinkle') || 
        (lowerTrimmed.includes('star') && lowerTrimmed.includes('little')) ||
        (lowerTrimmed.includes('foot') && lowerTrimmed.includes('peel'))) {
        return { isNoAnswer: true, reason: `song_title_reference: ${trimmed}` };
    }
    
    // ✅ FIX: Detect answers that don't contain any interview-relevant keywords
    // If answer is long enough but doesn't contain any professional/personal keywords, it might be irrelevant
    const interviewKeywords = [
        'i am', 'i have', 'i work', 'i do', 'my', 'me', 'myself', 'experience', 'skill', 'project',
        'job', 'career', 'education', 'degree', 'company', 'team', 'work', 'professional', 'background',
        'strength', 'weakness', 'goal', 'interest', 'motivation', 'hire', 'position', 'role'
    ];
    
    // Only apply this check for longer answers (more than 20 characters)
    // Short answers might be valid (e.g., "Yes", "No", "I agree")
    if (trimmed.length > 20) {
        let hasInterviewKeyword = false;
        for (const keyword of interviewKeywords) {
            if (lowerTrimmed.includes(keyword)) {
                hasInterviewKeyword = true;
                break;
            }
        }
        
        // If long answer has no interview keywords AND contains descriptive/audio words, it's likely irrelevant
        if (!hasInterviewKeyword && descriptiveCount >= 1) {
            return { isNoAnswer: true, reason: `no_interview_relevance: ${trimmed}` };
        }
    }
    
    return { isNoAnswer: false, reason: null };
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
            throw new Error(`STT API failed with status: ${sttResponse.status}`);
        }

        const sttData = await sttResponse.json();
        const rawUserAnswer = sttData.text || ''; // Use a temporary variable for clarity
        
        // ✅ FIX: Detect "No Answer" cases (empty, garbage phrases, low confidence)
        const noAnswerCheck = detectNoAnswer(rawUserAnswer);
        
        let userAnswer;
        if (noAnswerCheck.isNoAnswer) {
            // Log the detection reason (debug level)
            console.log(`[STAR INTERVIEW] No Answer detected: ${noAnswerCheck.reason}`);
            userAnswer = 'No Answer'; // Record exactly as "No Answer"
        } else {
            userAnswer = rawUserAnswer.trim(); // Use the cleaned answer
        }

        // Display user's answer (show "No Answer" if detected, otherwise show actual text)
        displayMessage('user', userAnswer);

        // Submit answer to backend (will be "No Answer" or actual answer)
        await submitAnswer(userAnswer);

    } catch (error) {
        console.error('Process audio error:', error);
        
        // If STT fails completely, treat as "No Answer"
        console.log('[STAR INTERVIEW] STT failed, treating as No Answer');
        const userAnswer = 'No Answer';
        displayMessage('user', userAnswer);
        await submitAnswer(userAnswer);
    }
}

async function submitAnswer(answer) {
    // ✅ FIX: Allow "No Answer" as a valid answer (exactly this string)
    // Empty answers are still rejected, but "No Answer" is accepted
    if (!answer || (!answer.trim() && answer !== 'No Answer')) {
        showUserFriendlyError(
            { message: 'I could not hear your answer. Please speak again.', originalError: new Error('Empty answer') },
            'submitAnswer',
            false
        );
        return;
    }

    if (!interviewSessionId || !currentQuestion) {
        showUserFriendlyError(new Error('No active interview session or question'), 'submitAnswer', false);
        return;
    }

    // Prevent double submission
    if (isLoading.submitAnswer) {
        console.warn('[SUBMIT ANSWER] Submit answer already in progress, ignoring duplicate call');
        return;
    }

    try {
        setLoadingState('submitAnswer', true);
        console.log('[SUBMIT ANSWER] Submitting STAR answer to backend...');
        
        // Use STAR-specific submit answer endpoint
        const response = await fetch(`${getApiBase()}/api/interview/star/${interviewSessionId}/submit-answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: currentQuestion,
                answer: answer,
                response_time: null  // Can be calculated if needed
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            const errorObj = {
                message: `Failed to submit answer: ${response.status}`,
                status: response.status,
                responseText: errorText,
                originalError: new Error(`HTTP ${response.status}: ${errorText}`)
            };
            throw errorObj;
        }

        const data = await response.json();
        
        console.log('[SUBMIT ANSWER] ✅ STAR answer submitted successfully');
        console.log('[SUBMIT ANSWER] STAR scores:', {
            star_structure: data.scores?.star_structure,
            situation: data.scores?.situation,
            task: data.scores?.task,
            action: data.scores?.action,
            result: data.scores?.result,
            overall: data.scores?.overall
        });
        
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
                console.log('[STAR INTERVIEW] Enqueueing AI response audio:', data.audio_url);
                enqueueAudio(data.audio_url);
            }
        }

        // Check if interview is complete (10 questions for STAR)
        const aiQuestionsCount = conversationHistory.filter(m => m.role === 'ai').length;
        if (data.interview_completed || aiQuestionsCount >= 10) {
            console.log(`[SUBMIT ANSWER] Interview completed: ${aiQuestionsCount} questions asked`);
            await completeInterview();
        } else {
            // FIX 10: Get next question after a short delay with race condition check
            // Pass the user's answer so backend can save it and use it for context-aware next question
            setTimeout(() => {
                // FIX 10: Check if getNextQuestion is already in progress to prevent duplicate calls
                if (!isLoading.getNextQuestion) {
                    getNextSTARQuestion(answer);  // Pass the answer for context-aware question generation
                } else {
                    console.warn('[SUBMIT ANSWER] getNextSTARQuestion already in progress, ignoring duplicate call');
                }
            }, 2000);
        }

        document.getElementById('voiceStatus').textContent = 'Click the microphone to record your answer';

    } catch (error) {
        const errorObj = {
            message: error.message || 'Failed to submit answer. Please try again.',
            status: error.status,
            originalError: error
        };
        showUserFriendlyError(errorObj, 'submitAnswer', true);
        document.getElementById('voiceStatus').textContent = 'Error submitting answer. Click the microphone to try again.';
        // Don't redirect - keep interview active
    } finally {
        setLoadingState('submitAnswer', false);
    }
}

async function getNextSTARQuestion(userAnswer = null) {
    if (!interviewSessionId) {
        console.error('[STAR INTERVIEW] No session ID available');
        showError('No interview session found. Please start the interview again.');
        return;
    }

    // Prevent double submission
    if (isLoading.getNextQuestion) {
        console.warn('[STAR INTERVIEW] Get next question already in progress, ignoring duplicate call');
        return;
    }

    try {
        setLoadingState('getNextQuestion', true);
        
        // Hide loading message if still visible
        const loadingMsg = document.getElementById('loadingMessage');
        if (loadingMsg) {
            loadingMsg.classList.add('hidden');
        }
        
        console.log('[STAR INTERVIEW] Fetching next question from backend...');
        if (userAnswer) {
            console.log('[STAR INTERVIEW] Sending user answer for context-aware question generation');
        }
        
        // Call backend endpoint to get next AI-generated STAR question
        // Send user_answer if provided so backend can save it and use it for context-aware generation
        const requestBody = {};
        if (userAnswer) {
            requestBody.user_answer = userAnswer;
        }
        
        const response = await fetch(`${getApiBase()}/api/interview/star/${interviewSessionId}/next-question`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Backend error: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        
        // Check if interview is completed
        if (data.interview_completed) {
            console.log('[STAR INTERVIEW] Interview completed:', data.message);
            await completeInterview();
            return;
        }
        
        // Extract question data from response
        const nextQuestion = data.question;
        const audioUrl = data.audio_url || data.audioUrl; // Try both possible field names
        const questionNumber = data.question_number || conversationHistory.filter(m => m.role === 'ai').length + 1;
        
        if (!nextQuestion) {
            throw new Error('No question received from backend');
        }
        
        console.log('[STAR INTERVIEW] Received question:', nextQuestion.substring(0, 50) + '...');
        console.log('[STAR INTERVIEW] Audio URL from response:', audioUrl);
        console.log('[STAR INTERVIEW] Full response data keys:', Object.keys(data));
        
        // Update current question
        currentQuestion = nextQuestion;
        
        // Update local conversation history to reflect backend's source of truth
        // Note: If user_answer was sent, it's already saved in backend and included in conversation history
        // We only need to add the newly received question to local history
        conversationHistory.push({
            role: 'ai',
            content: nextQuestion,
            audio_url: audioUrl,
            question_number: questionNumber
        });
        
        console.log('[STAR INTERVIEW] ✅ Updated local conversation history with new question');
        
        // Display question with audio URL
        displayMessage('ai', nextQuestion, audioUrl);
        
        // ✅ FIX: ALWAYS play audio for every question (same behavior as Technical Interview)
        // Use setTimeout to ensure audio plays after UI update, but don't wait for user interaction
        // For subsequent questions, user has already interacted (recorded answer), so autoplay should work
        setTimeout(() => {
            if (audioUrl && audioUrl.trim()) {
                console.log('[STAR INTERVIEW] ✅ Enqueueing next question audio:', audioUrl);
                enqueueAudio(audioUrl);
            } else {
                // Fallback - generate TTS from question text if audio_url is missing
                console.warn('[STAR INTERVIEW] ⚠️ No audioUrl provided, enqueueing TTS from question text');
                if (nextQuestion) {
                    enqueueAudio(nextQuestion);
                } else {
                    console.error('[STAR INTERVIEW] ❌ No question text available for TTS fallback');
                    document.getElementById('voiceStatus').textContent = 'Click the microphone to record your answer';
                }
            }
        }, 100); // Small delay to ensure UI is updated

    } catch (error) {
        console.error('[STAR INTERVIEW] ❌ Get question error:', error);
        const errorMsg = `Failed to get question from backend: ${error.message || 'Please try again.'}`;
        showError(errorMsg);
        document.getElementById('voiceStatus').textContent = 'Error occurred. Please try recording again or start a new interview.';
        
        // No fallback to hardcoded questions - all questions must come from backend
        // If backend fails, we can only complete the interview if we have enough questions
        const questionCount = conversationHistory.filter(m => m.role === 'ai').length;
        if (questionCount >= 5) {
            console.log('[STAR INTERVIEW] Interview completed due to question count (5 questions reached)');
            await completeInterview();
        } else {
            // Show error but don't try to continue with hardcoded questions
            console.error('[STAR INTERVIEW] Cannot continue: Backend question generation failed and interview is incomplete');
            alert('Unable to get next question from the server. Please try refreshing the page or starting a new interview.');
        }
    } finally {
        // FIX: Ensure loading state is always reset
        setLoadingState('getNextQuestion', false);
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

// Helper function to set score badge based on score
function setScoreBadge(score) {
    const scoreBadgeEl = document.getElementById('scoreBadge');
    if (scoreBadgeEl) {
        const numericScore = typeof score === 'string' ? parseInt(score) : Math.round(score);
        if (numericScore >= 80) {
            scoreBadgeEl.textContent = '⭐⭐⭐ Strong';
        } else if (numericScore >= 60) {
            scoreBadgeEl.textContent = '⭐⭐ Improving';
        } else {
            scoreBadgeEl.textContent = '⭐ Beginner';
        }
    }
}

// Helper function to set score message based on score
function setScoreMessage(score) {
    const scoreMessageEl = document.getElementById('scoreMessage');
    if (scoreMessageEl) {
        const numericScore = typeof score === 'string' ? parseInt(score) : Math.round(score);
        if (numericScore >= 80) {
            scoreMessageEl.textContent = 'Outstanding performance! You demonstrated strong STAR method skills.';
        } else if (numericScore >= 60) {
            scoreMessageEl.textContent = 'Good work! With more practice, you can improve your STAR responses.';
        } else {
            scoreMessageEl.textContent = 'Keep practicing to improve your STAR responses!';
        }
    }
}

// Display performance breakdown for STAR components
function displayPerformanceBreakdown(feedback) {
    const components = [
        { key: 'situation_score', id: 'situation', label: 'Situation' },
        { key: 'task_score', id: 'task', label: 'Task' },
        { key: 'action_score', id: 'action', label: 'Action' },
        { key: 'result_score', id: 'result', label: 'Result' },
        { key: 'star_structure_score', id: 'structure', label: 'STAR Structure' }
    ];
    
    components.forEach(component => {
        const score = Math.round(feedback[component.key] || 0);
        const scoreEl = document.getElementById(component.id + 'Score');
        const fillEl = document.getElementById(component.id + 'Fill');
        
        if (scoreEl) {
            scoreEl.textContent = score;
        }
        
        if (fillEl) {
            // Animate the bar fill
            setTimeout(() => {
                fillEl.style.width = score + '%';
            }, 100);
        }
    });
}

async function generateFeedback() {
    if (!interviewSessionId) {
        const error = new Error('No interview session found. Cannot generate feedback.');
        showUserFriendlyError(error, 'generateFeedback', false);
        generateBasicFeedback();
        return;
    }

    // Prevent double submission
    if (isLoading.generateFeedback) {
        console.warn('[FEEDBACK] Generate feedback already in progress, ignoring duplicate call');
        return;
    }

    try {
        setLoadingState('generateFeedback', true);
        console.log('[FEEDBACK] Requesting STAR feedback from backend...');
        
        // Use STAR-specific feedback endpoint
        const response = await fetch(`${getApiBase()}/api/interview/star/${interviewSessionId}/feedback`, {
            method: 'GET'
        });

        if (!response.ok) {
            const errorText = await response.text();
            const errorObj = {
                message: `Failed to generate feedback: ${response.status}`,
                status: response.status,
                responseText: errorText,
                originalError: new Error(`HTTP ${response.status}: ${errorText}`)
            };
            
            // Log error but fallback to basic feedback
            console.error('[FEEDBACK] STAR feedback endpoint error:', response.status, errorText);
            showUserFriendlyError(errorObj, 'generateFeedback', true);
            
            // Fallback to basic feedback if endpoint fails
            console.warn('[FEEDBACK] STAR feedback endpoint failed, generating basic feedback');
            generateBasicFeedback();
            return;
        }

        const feedback = await response.json();

        if (!feedback) {
            console.warn('[FEEDBACK] No feedback data received, generating basic feedback');
            generateBasicFeedback();
            return;
        }

        console.log('[FEEDBACK] ✅ STAR feedback received successfully');
        console.log('[FEEDBACK] Feedback data:', {
            overall_score: feedback.overall_score,
            star_structure_score: feedback.star_structure_score,
            situation_score: feedback.situation_score,
            task_score: feedback.task_score,
            action_score: feedback.action_score,
            result_score: feedback.result_score,
            question_count: feedback.question_count
        });
        
        // Display feedback
        const overallScore = Math.round(feedback.overall_score || 0);
        document.getElementById('overallScore').textContent = overallScore;
        setScoreBadge(overallScore);
        setScoreMessage(overallScore);
        
        // Set personalized welcome message
        const welcomeTextEl = document.getElementById('welcomeText');
        if (welcomeTextEl) {
            if (overallScore >= 80) {
                welcomeTextEl.textContent = 'Outstanding work! You completed your STAR interview with excellent performance. Here\'s your personalized breakdown.';
            } else if (overallScore >= 60) {
                welcomeTextEl.textContent = 'Great job completing your STAR interview! Here\'s your personalized performance report to help you improve.';
            } else {
                welcomeTextEl.textContent = 'Thank you for completing your STAR interview! Here\'s your personalized feedback to help you improve.';
            }
        }
        
        // Display interview participation metrics
        const questionCount = feedback.question_count || 0;
        const userMessages = conversationHistory.filter(m => m.role === 'user');
        const answeredCount = userMessages.length;
        const participationRate = questionCount > 0 ? Math.round((answeredCount / questionCount) * 100) : 0;
        
        const questionsAnsweredEl = document.getElementById('questionsAnswered');
        if (questionsAnsweredEl) {
            questionsAnsweredEl.textContent = answeredCount;
        }
        
        const participationRateEl = document.getElementById('participationRate');
        if (participationRateEl) {
            participationRateEl.textContent = participationRate + '%';
        }
        
        const participationNoteEl = document.getElementById('participationNote');
        if (participationNoteEl) {
            if (participationRate >= 80) {
                participationNoteEl.textContent = 'Excellent! You actively engaged with all questions throughout the interview.';
            } else if (participationRate >= 60) {
                participationNoteEl.textContent = 'Good participation! You answered most of the questions asked.';
            } else {
                participationNoteEl.textContent = 'Try to answer more questions in your next interview to get better feedback.';
            }
        }
        
        // Display performance breakdown (STAR component scores)
        displayPerformanceBreakdown(feedback);
        
        // Display STAR-specific scores if UI elements exist
        const communicationScoreEl = document.getElementById('communicationScore');
        if (communicationScoreEl && feedback.communication_score !== undefined) {
            communicationScoreEl.textContent = Math.round(feedback.communication_score);
        }
        
        const culturalFitScoreEl = document.getElementById('culturalFitScore');
        if (culturalFitScoreEl && feedback.cultural_fit_score !== undefined) {
            culturalFitScoreEl.textContent = Math.round(feedback.cultural_fit_score);
        }
        
        const motivationScoreEl = document.getElementById('motivationScore');
        if (motivationScoreEl && feedback.motivation_score !== undefined) {
            motivationScoreEl.textContent = Math.round(feedback.motivation_score);
        }
        
        const clarityScoreEl = document.getElementById('clarityScore');
        if (clarityScoreEl && feedback.clarity_score !== undefined) {
            clarityScoreEl.textContent = Math.round(feedback.clarity_score);
        }
        
        const strengthsList = document.getElementById('strengthsList');
        if (strengthsList) {
            const strengths = feedback.strengths || [];
            strengthsList.innerHTML = strengths.length > 0 
                ? strengths.map(s => `<li>${s}</li>`).join('')
                : '<li>Keep practicing to build your strengths!</li>';
        }

        const improvementsList = document.getElementById('improvementsList');
        if (improvementsList) {
            const improvements = feedback.areas_for_improvement || [];
            improvementsList.innerHTML = improvements.length > 0
                ? improvements.map(a => `<li>${a}</li>`).join('')
                : '<li>Great job! Continue refining your STAR responses.</li>';
        }

        const recommendationsList = document.getElementById('recommendationsList');
        if (recommendationsList) {
            const recommendations = feedback.recommendations || [];
            recommendationsList.innerHTML = recommendations.length > 0
                ? recommendations.map(r => `<li>${r}</li>`).join('')
                : '<li>Keep practicing your STAR method responses!</li>';
        }

        const feedbackSummaryEl = document.getElementById('feedbackSummary');
        if (feedbackSummaryEl) {
            feedbackSummaryEl.textContent = feedback.feedback_summary || 'No summary available.';
        }

        const feedbackLoading = document.getElementById('feedbackLoading');
        const feedbackContent = document.getElementById('feedbackContent');
        if (feedbackLoading) feedbackLoading.classList.add('hidden');
        if (feedbackContent) feedbackContent.classList.remove('hidden');

    } catch (error) {
        const errorObj = {
            message: error.message || 'Failed to generate feedback. Please try again.',
            status: error.status,
            originalError: error
        };
        showUserFriendlyError(errorObj, 'generateFeedback', true);
        
        // Fallback to basic feedback on error
        generateBasicFeedback();
    } finally {
        setLoadingState('generateFeedback', false);
    }
}

function generateBasicFeedback() {
    // Generate fallback feedback when backend STAR feedback endpoint is unavailable.
    // This uses the actual conversation history so it still reflects what happened in the interview.
    const userMessages = conversationHistory.filter(m => m.role === 'user');
    const answerCount = userMessages.length;

    function isValidAnswer(answerText) {
        if (!answerText || typeof answerText !== 'string') return false;
        const trimmed = answerText.trim();
        if (trimmed === '' || trimmed === 'No Answer') return false;
        const words = trimmed.split(/\s+/).filter(w => w.length > 2);
        return words.length >= 3;
    }

    const validAnswers = userMessages.filter(m => isValidAnswer(m.content));
    const validAnswerCount = validAnswers.length;

    // If no valid answers, show 0 score and clear guidance
    if (validAnswerCount === 0) {
        document.getElementById('overallScore').textContent = '0';
        setScoreBadge(0);
        setScoreMessage(0);
        
        // Set participation metrics
        const questionsAnsweredEl = document.getElementById('questionsAnswered');
        if (questionsAnsweredEl) questionsAnsweredEl.textContent = '0';
        const participationRateEl = document.getElementById('participationRate');
        if (participationRateEl) participationRateEl.textContent = '0%';
        const participationNoteEl = document.getElementById('participationNote');
        if (participationNoteEl) {
            participationNoteEl.textContent = 'No answers were provided during this interview.';
        }
        
        // Set performance breakdown to 0
        displayPerformanceBreakdown({
            situation_score: 0,
            task_score: 0,
            action_score: 0,
            result_score: 0,
            star_structure_score: 0
        });
        
        document.getElementById('strengthsList').innerHTML = '<li>No valid response detected.</li>';
        document.getElementById('improvementsList').innerHTML = '<li>Please provide spoken answers to receive accurate STAR feedback.</li>';
        document.getElementById('recommendationsList').innerHTML = '<li>Try answering all STAR questions with clear Situation, Task, Action, and Result.</li>';
        document.getElementById('feedbackSummary').textContent = 'Interview ended early with no valid responses.';
        document.getElementById('feedbackLoading').classList.add('hidden');
        document.getElementById('feedbackContent').classList.remove('hidden');
        return;
    }

    const totalWords = validAnswers.reduce((sum, m) => {
        if (!m.content) return sum;
        return sum + m.content.split(/\s+/).filter(Boolean).length;
    }, 0);
    const avgWords = validAnswerCount > 0 ? totalWords / validAnswerCount : 0;

    // Heuristic score based on depth and number of valid answers (kept conservative)
    let score = 0;
    if (validAnswerCount >= 4) score += 20;
    else if (validAnswerCount >= 2) score += 10;
    if (avgWords >= 50) score += 25;
    else if (avgWords >= 30) score += 18;
    else if (avgWords >= 15) score += 8;
    score = Math.max(0, Math.min(85, Math.round(score)));

    const strengths = [];
    const improvements = [];
    const recommendations = [];

    strengths.push(`You provided ${validAnswerCount} STAR example${validAnswerCount > 1 ? 's' : ''} during the interview.`);

    if (avgWords >= 35) {
        strengths.push('Your answers had reasonable detail and context for behavioral situations.');
    } else if (avgWords >= 15) {
        improvements.push('Some answers were quite brief; adding more detail for Situation, Task, Action, and Result will make them stronger.');
    } else {
        improvements.push('Answers were very short; try expanding each story with more context, actions, and results.');
    }

    improvements.push('Make sure each answer clearly covers all four STAR parts: Situation, Task, Action, and Result.');

    recommendations.push('Write down 3–5 STAR stories and practice telling them out loud with clear outcomes and metrics.');

    document.getElementById('overallScore').textContent = String(score);
    setScoreBadge(score);
    setScoreMessage(score);
    
    // Set participation metrics for basic feedback
    const totalQuestions = answerCount; // Use answerCount as total questions asked
    const questionsAnsweredEl = document.getElementById('questionsAnswered');
    if (questionsAnsweredEl) questionsAnsweredEl.textContent = validAnswerCount;
    const participationRateEl = document.getElementById('participationRate');
    if (participationRateEl) {
        const rate = totalQuestions > 0 ? Math.round((validAnswerCount / totalQuestions) * 100) : 0;
        participationRateEl.textContent = rate + '%';
    }
    const participationNoteEl = document.getElementById('participationNote');
    if (participationNoteEl) {
        if (totalQuestions > 0 && validAnswerCount >= totalQuestions * 0.8) {
            participationNoteEl.textContent = 'Excellent! You actively engaged with all questions throughout the interview.';
        } else if (totalQuestions > 0 && validAnswerCount >= totalQuestions * 0.6) {
            participationNoteEl.textContent = 'Good participation! You answered most of the questions asked.';
        } else {
            participationNoteEl.textContent = 'Try to answer more questions in your next interview to get better feedback.';
        }
    }
    
    // Set basic performance breakdown (estimate based on score)
    const estimatedComponentScore = Math.max(0, Math.min(100, score));
    displayPerformanceBreakdown({
        situation_score: estimatedComponentScore,
        task_score: estimatedComponentScore,
        action_score: estimatedComponentScore,
        result_score: estimatedComponentScore,
        star_structure_score: estimatedComponentScore
    });
    
    document.getElementById('strengthsList').innerHTML = strengths.map(s => `<li>${s}</li>`).join('');
    document.getElementById('improvementsList').innerHTML = improvements.map(a => `<li>${a}</li>`).join('');
    document.getElementById('recommendationsList').innerHTML = recommendations.map(r => `<li>${r}</li>`).join('');
    document.getElementById('feedbackSummary').textContent =
        'We could not load the full AI report, so this quick summary is based on how many STAR examples you shared and how detailed they were. For a richer, fully personalized report, please try the interview again when your connection is stable.';

    document.getElementById('feedbackLoading').classList.add('hidden');
    document.getElementById('feedbackContent').classList.remove('hidden');
}

function displayMessage(role, content, audioUrl = null) {
    const container = document.getElementById('conversationContainer');
    if (!container) {
        console.error('[STAR INTERVIEW] Conversation container not found');
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

async function playAudio(textOrUrl, retryCount = 0) {
    const MAX_RETRIES = 2;
    if (!textOrUrl) {
        console.warn('[STAR INTERVIEW TTS] No audio URL or text provided');
        return; // Same behavior as Technical: simple early return
    }

    // Stop any currently playing audio instance before starting a new one.
    // Queueing / serial order is handled by enqueueAudio + playNextFromStarQueue.
    if (currentAudio && !currentAudio.paused) {
        console.log('[STAR INTERVIEW TTS] Stopping previous audio before starting new one');
        currentAudio.pause();
        currentAudio.currentTime = 0;
        if (currentAudio.src && currentAudio.src.startsWith('blob:')) {
            URL.revokeObjectURL(currentAudio.src);
        }
    }

    try {
        console.log('[STAR INTERVIEW TTS] Starting audio playback:', textOrUrl);
        isAudioPlaying = true;

        const voiceStatus = document.getElementById('voiceStatus');
        const voiceButton = document.getElementById('voiceButton');
        if (voiceStatus) voiceStatus.textContent = 'Question is being spoken...';
        if (voiceButton) voiceButton.classList.add('listening');

        let text = textOrUrl;
        let fullUrl = null;

        // Handle both URL and plain text (like Technical interview)
        if (typeof textOrUrl === 'string' && textOrUrl.startsWith('http')) {
            // Try to extract text from query parameter (?text=...)
            try {
                const url = new URL(textOrUrl);
                const textParam = url.searchParams.get('text');
                if (textParam && textParam.trim()) {
                    text = decodeURIComponent(textParam);
                } else {
                    // Direct audio URL with no text param – play it directly
                    fullUrl = textOrUrl;
                }
            } catch (e) {
                // Not a valid URL, treat as text
                console.warn('[STAR INTERVIEW TTS] Invalid URL, treating as plain text:', e.message);
                text = textOrUrl;
                fullUrl = null;
            }
        } else {
            // Plain text (question text or AI response)
            text = textOrUrl;
            fullUrl = null;
        }

        // If we don't have a direct URL, generate TTS from text via POST (like Technical)
        if (!fullUrl) {
            if (!text || !text.trim()) {
                console.warn('[STAR INTERVIEW TTS] No text available for TTS generation');
                return;
            }

            console.log('[STAR INTERVIEW TTS] Generating TTS from text:', text.substring(0, 80) + '...');

            const response = await fetch(`${getApiBase()}/api/interview/text-to-speech`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: text.trim() })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[STAR INTERVIEW TTS] TTS API error:', response.status, errorText);

                // Retry on server errors (5xx) like Technical
                if ((response.status >= 500 || response.status === 503) && retryCount < MAX_RETRIES) {
                    await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
                    return playAudio(textOrUrl, retryCount + 1);
                }

                throw new Error(`TTS failed: ${response.status} - ${errorText}`);
            }

            const audioBlob = await response.blob();
            if (audioBlob.size === 0) {
                throw new Error('Empty audio blob received from TTS endpoint');
            }

            fullUrl = URL.createObjectURL(audioBlob);
            console.log('[STAR INTERVIEW TTS] Created blob URL:', fullUrl.substring(0, 80) + '...');
        }

        const audio = new Audio(fullUrl);
        currentAudio = audio;

        // Attach listeners BEFORE play()
        audio.onloadedmetadata = () => {
            console.log('[STAR INTERVIEW TTS] loadedmetadata');
        };
        audio.oncanplaythrough = () => {
            console.log('[STAR INTERVIEW TTS] canplaythrough');
        };
        audio.onplaying = () => {
            console.log('[STAR INTERVIEW TTS] playing');
        };

        audio.onerror = (error) => {
            console.error('[STAR INTERVIEW TTS] ❌ Audio playback error:', error);
            console.error('[STAR INTERVIEW TTS] Audio error details:', {
                code: audio.error?.code,
                message: audio.error?.message,
                src: audio.src?.substring(0, 120)
            });
            isAudioPlaying = false;
            if (voiceButton) voiceButton.classList.remove('listening');
            if (voiceStatus) voiceStatus.textContent = 'Click the microphone to record your answer';

            if (fullUrl && fullUrl.startsWith('blob:')) {
                URL.revokeObjectURL(fullUrl);
            }

            if (retryCount < MAX_RETRIES) {
                console.log(`[STAR INTERVIEW TTS] Retrying audio playback (attempt ${retryCount + 1}/${MAX_RETRIES})...`);
                setTimeout(() => playAudio(textOrUrl, retryCount + 1), 1000 * (retryCount + 1));
            } else {
                showManualPlayButton(textOrUrl);
                // After a terminal error, advance the queue (skip this item)
                setTimeout(() => playNextFromStarQueue(), 100);
            }
        };

        audio.onended = () => {
            console.log('[STAR INTERVIEW TTS] ✅ Audio playback completed');
            isAudioPlaying = false;
            if (voiceButton) voiceButton.classList.remove('listening');
            if (voiceStatus) voiceStatus.textContent = 'Click the microphone to record your answer';

            if (fullUrl && fullUrl.startsWith('blob:')) {
                URL.revokeObjectURL(fullUrl);
            }

            // Audio finished successfully; play next queued item if any
            setTimeout(() => playNextFromStarQueue(), 100);
        };

        audio.onloadstart = () => {
            console.log('[STAR INTERVIEW TTS] Audio loading started');
        };

        // Attempt to play audio with promise handling (like Technical)
        console.log('[STAR INTERVIEW TTS] Attempting to play audio...');
        try {
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                await playPromise;
                console.log('[STAR INTERVIEW TTS] ✅ Audio playback started successfully');
            }
        } catch (playError) {
            console.error('[STAR INTERVIEW TTS] Error starting playback:', playError);
            if (playError.name === 'NotAllowedError') {
                console.warn('[STAR INTERVIEW TTS] ⚠️ Autoplay blocked by browser policy');
                isAudioPlaying = false;
                if (voiceButton) voiceButton.classList.remove('listening');
                if (voiceStatus) {
                    voiceStatus.textContent = 'Click the play button below to hear the question';
                }
                showManualPlayButton(textOrUrl);
                // Do NOT advance the queue here; wait for user interaction to start audio
                return;
            }
            throw playError;
        }
    } catch (error) {
        console.error('[STAR INTERVIEW TTS] ❌ Error in playAudio:', error);
        console.error('[STAR INTERVIEW TTS] Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        isAudioPlaying = false;
        const voiceButton = document.getElementById('voiceButton');
        const voiceStatus = document.getElementById('voiceStatus');
        if (voiceButton) voiceButton.classList.remove('listening');
        if (voiceStatus) voiceStatus.textContent = 'Click the microphone to record your answer';

        // Retry on network/loading errors (but not autoplay errors)
        if (retryCount < MAX_RETRIES &&
            (error.message.includes('fetch') ||
             error.message.includes('network') ||
             error.message.includes('Failed to load') ||
             error.message.includes('NetworkError'))) {
            console.log(`[STAR INTERVIEW TTS] Retrying due to network error (attempt ${retryCount + 1}/${MAX_RETRIES})...`);
            setTimeout(() => playAudio(textOrUrl, retryCount + 1), 1000 * (retryCount + 1));
        } else if (retryCount >= MAX_RETRIES) {
            showManualPlayButton(textOrUrl);
            // After giving up on this item, advance the queue
            setTimeout(() => playNextFromStarQueue(), 100);
        }
    }
}

// Helper function to show manual play button when autoplay fails
function showManualPlayButton(audioUrl) {
    const container = document.getElementById('conversationContainer');
    if (!container) return;
    
    // Check if manual play button already exists
    let existingButton = document.getElementById('manualPlayButton');
    if (existingButton) {
        existingButton.onclick = () => enqueueAudio(audioUrl);
        return;
    }
    
    // Create manual play button
    const playButton = document.createElement('button');
    playButton.id = 'manualPlayButton';
    playButton.className = 'btn btn-primary';
    playButton.style.cssText = 'margin: 10px auto; display: block; padding: 10px 20px;';
    playButton.textContent = '▶ Play Question Audio';
    playButton.onclick = () => {
        enqueueAudio(audioUrl);
        playButton.remove();
    };
    
    // Insert after last message or at end of container
    const lastMessage = container.lastElementChild;
    if (lastMessage) {
        lastMessage.appendChild(playButton);
    } else {
        container.appendChild(playButton);
    }
    
    console.log('[STAR INTERVIEW TTS] Manual play button displayed');
}

/**
 * Show user-friendly error message
 * Maps technical errors to clear, actionable messages for users
 * @param {Error|string} error - The error object or error message
 * @param {string} context - Context where the error occurred (e.g., 'startInterview', 'submitAnswer')
 * @param {boolean} showRetry - Whether to show a retry button for recoverable errors
 */
function showUserFriendlyError(error, context = 'unknown', showRetry = false) {
    // Log technical error to console for developers
    console.error(`[STAR INTERVIEW ERROR] Context: ${context}`, error);
    
    let userMessage = 'An unexpected error occurred. Please try again.';
    let isRecoverable = false;
    
    // Extract error message
    const errorMessage = error?.message || error?.toString() || String(error);
    const errorStatus = error?.status || error?.response?.status;
    
    // Map technical errors to user-friendly messages
    if (errorMessage.includes('NetworkError') || 
        errorMessage.includes('Failed to fetch') || 
        errorMessage.includes('network') ||
        errorMessage.includes('Network request failed')) {
        userMessage = 'Network connection error. Please check your internet connection and try again.';
        isRecoverable = true;
    } else if (errorStatus === 404 || errorMessage.includes('404') || errorMessage.includes('not found')) {
        if (context === 'startInterview') {
            userMessage = 'User profile not found. Please upload a resume first to create your profile.';
        } else if (context === 'getNextQuestion' || context === 'submitAnswer') {
            userMessage = 'Interview session not found. Please start a new interview.';
        } else {
            userMessage = 'Resource not found. Please try starting a new interview.';
        }
        isRecoverable = false;
    } else if (errorStatus === 400 || errorMessage.includes('400') || errorMessage.includes('Bad Request')) {
        userMessage = 'Invalid request. Please check your input and try again.';
        isRecoverable = true;
    } else if (errorStatus === 500 || errorMessage.includes('500') || errorMessage.includes('Internal Server Error')) {
        userMessage = 'Server error occurred. Please try again in a moment.';
        isRecoverable = true;
    } else if (errorMessage.includes('microphone') || errorMessage.includes('Microphone')) {
        userMessage = 'Microphone access denied. Please allow microphone access in your browser settings and try again.';
        isRecoverable = true;
    } else if (errorMessage.includes('session') || errorMessage.includes('Session')) {
        userMessage = 'Interview session expired. Please start a new interview.';
        isRecoverable = false;
    } else if (errorMessage.includes('user_id') || errorMessage.includes('user profile')) {
        userMessage = 'User profile not found. Please upload a resume first.';
        isRecoverable = false;
    } else if (errorMessage) {
        // Use error message if it's already user-friendly
        userMessage = errorMessage;
    }
    
    // Display error in UI
    // If showing retry button, it will display the error message, so don't show it twice
    if (showRetry && isRecoverable) {
        // Retry button will display the error message, so skip showError()
        showRetryButton(context, userMessage);
    } else {
        // No retry button, so show the error message directly
        showError(userMessage);
    }
    
    return { userMessage, isRecoverable };
}

/**
 * Show retry button for recoverable errors
 */
function showRetryButton(context, errorMessage) {
    const container = document.getElementById('conversationContainer');
    if (!container) return;
    
    // Check if retry button already exists
    let retryContainer = document.getElementById('retryErrorContainer');
    if (!retryContainer) {
        retryContainer = document.createElement('div');
        retryContainer.id = 'retryErrorContainer';
        retryContainer.className = 'error-retry-container';
        retryContainer.style.cssText = 'margin: 15px 0; padding: 15px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;';
        container.appendChild(retryContainer);
    }
    
    retryContainer.innerHTML = `
        <div style="margin-bottom: 10px;">
            <strong>⚠️ ${errorMessage}</strong>
        </div>
        <button id="retryButton" style="background: #ff9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
            🔄 Retry
        </button>
    `;
    
    // Add retry handler
    const retryButton = document.getElementById('retryButton');
    retryButton.onclick = () => {
        retryContainer.remove();
        retryAction(context);
    };
    
    container.scrollTop = container.scrollHeight;
}

/**
 * Retry action based on context
 */
async function retryAction(context) {
    try {
        switch (context) {
            case 'startInterview':
                await startInterview();
                break;
            case 'submitAnswer':
                // Re-enable submit button, user can try again
                setLoadingState('submitAnswer', false);
                document.getElementById('voiceStatus').textContent = 'Click the microphone to record your answer';
                break;
            case 'getNextQuestion':
                await getNextSTARQuestion();
                break;
            case 'generateFeedback':
                await generateFeedback();
                break;
            case 'playAudio':
                // Audio retry is handled within playAudio function
                break;
            default:
                console.warn(`[STAR INTERVIEW] Unknown retry context: ${context}`);
        }
    } catch (error) {
        showUserFriendlyError(error, context, true);
    }
}

/**
 * Set loading state for a specific operation
 */
function setLoadingState(operation, loading) {
    isLoading[operation] = loading;
    
    // Update UI based on operation
    switch (operation) {
        case 'startInterview':
            const startBtn = document.getElementById('startInterviewBtn');
            if (startBtn) {
                startBtn.disabled = loading;
                startBtn.textContent = loading ? 'Starting...' : 'Start STAR Interview';
            }
            break;
        case 'submitAnswer':
            const voiceBtn = document.getElementById('voiceButton');
            if (voiceBtn) {
                voiceBtn.disabled = loading;
            }
            const voiceStatus = document.getElementById('voiceStatus');
            if (voiceStatus && loading) {
                voiceStatus.textContent = 'Processing...';
            }
            break;
        case 'getNextQuestion':
            // No specific button for this, but we can show loading in status
            break;
        case 'generateFeedback':
            const feedbackLoading = document.getElementById('feedbackLoading');
            if (feedbackLoading) {
                if (loading) {
                    feedbackLoading.classList.remove('hidden');
                } else {
                    feedbackLoading.classList.add('hidden');
                }
            }
            break;
    }
}

function showError(message) {
    const container = document.getElementById('conversationContainer');
    if (!container) {
        // Fallback to alert if container not found
        alert(message);
        return;
    }
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    container.appendChild(errorDiv);
    container.scrollTop = container.scrollHeight;
}

// Modal confirmation function (replaces browser confirm)
function showConfirmation(title, message) {
    console.log('[STAR INTERVIEW] showConfirmation called with:', { title, message });
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmationModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalMessage = document.getElementById('modalMessage');
        const confirmBtn = document.getElementById('modalConfirmBtn');
        const cancelBtn = document.getElementById('modalCancelBtn');

        // Error check: ensure all elements exist
        if (!modal || !modalTitle || !modalMessage || !confirmBtn || !cancelBtn) {
            console.error('[STAR INTERVIEW] Modal elements not found:', {
                modal: !!modal,
                modalTitle: !!modalTitle,
                modalMessage: !!modalMessage,
                confirmBtn: !!confirmBtn,
                cancelBtn: !!cancelBtn
            });
            // DO NOT fallback to browser confirm - this is the old behavior we're replacing
            // Instead, show error and resolve false
            alert('Error: Modal elements not found. Please refresh the page.');
            resolve(false);
            return;
        }

        // Set modal content
        modalTitle.textContent = title;
        modalMessage.textContent = message;

        // Show modal
        modal.classList.add('show');

        // Handle confirm - use once: true to auto-remove after first click
        const handleConfirm = (e) => {
            e.preventDefault();
            e.stopPropagation();
            modal.classList.remove('show');
            resolve(true);
        };

        // Handle cancel - use once: true to auto-remove after first click
        const handleCancel = (e) => {
            e.preventDefault();
            e.stopPropagation();
            modal.classList.remove('show');
            resolve(false);
        };

        // Remove any existing listeners by cloning and replacing buttons
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
        
        const newCancelBtn = cancelBtn.cloneNode(true);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
        
        // Get fresh references to the new buttons
        const finalConfirmBtn = document.getElementById('modalConfirmBtn');
        const finalCancelBtn = document.getElementById('modalCancelBtn');
        
        // Add event listeners to the new buttons
        finalConfirmBtn.addEventListener('click', handleConfirm, { once: true });
        finalCancelBtn.addEventListener('click', handleCancel, { once: true });

        // Prevent closing by clicking outside (as per requirements)
        // No event listener on overlay, so clicking outside won't close modal
    });
}

async function endInterview() {
    console.log('[STAR INTERVIEW] endInterview called');
    
    const confirmed = await showConfirmation(
        'End STAR Interview?',
        'Are you sure you want to end your STAR Interview? Your progress will be saved.'
    );
    
    console.log('[STAR INTERVIEW] User confirmed:', confirmed);
    
    if (confirmed) {
        interviewActive = false;
        
        if (isRecording) {
            stopRecording();
        }

        if (interviewSessionId) {
            try {
                // FIX: Use STAR-specific endpoint instead of technical endpoint
                const response = await fetch(`${getApiBase()}/api/interview/star/${interviewSessionId}/end`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    // Log successful attempt to end session
                    console.log(`[STAR INTERVIEW] End signal sent for session: ${interviewSessionId}`);
                } else {
                    console.warn(`[STAR INTERVIEW] End signal returned status: ${response.status}`);
                }
            } catch (error) {
                // Keep existing robust error logging
                console.error('[STAR INTERVIEW] Error sending end signal to backend:', error);
                // NOTE: Consider adding showUserFriendlyError() here (Error 7 improvement)
            }
        }

        await completeInterview();
    }
}

