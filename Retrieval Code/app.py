from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from search import ClipSearchEngine
import uvicorn
import base64
from db import SupabaseConnector


app = FastAPI(title="Dual-Purpose Search Engine")

# Initialize search engine
search_engine = ClipSearchEngine()

# Model for search query
class SearchQuery(BaseModel):
    query: str
    mode: str = "surveillance"  # Default to surveillance mode

# HTML content
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dual-Purpose Search</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f5f8fa;
        }

        .card {
            border-radius: 12px;
            overflow: hidden;
        }

        #chat-container {
            height: 600px;
            overflow-y: auto;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        .system-message {
            background-color: #e3f2fd;
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 15px;
            max-width: 85%;
        }

        .pcb-system-message {
            background-color: #e8f5e9;
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 15px;
            max-width: 85%;
        }

        .user-message {
            background-color: #e1f5fe;
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 15px;
            max-width: 85%;
            margin-left: auto;
            text-align: right;
        }

        .ai-message {
            background-color: #f5f5f5;
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 15px;
            max-width: 85%;
        }

        .result-item {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .result-name {
            color: #1565c0;
            margin-bottom: 5px;
        }

        .pcb-result-name {
            color: #2e7d32;
            margin-bottom: 5px;
        }

        .result-relevance {
            color: #388e3c;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }

        .result-description {
            color: #616161;
            margin-bottom: 10px;
        }

        .image-container {
            margin-top: 10px;
            width: 100%;
            position: relative;
            overflow: hidden;
            border-radius: 6px;
        }

        .result-image {
            width: 100%;
            height: auto;
            border-radius: 6px;
            transition: transform 0.3s ease;
        }

        .result-image:hover {
            transform: scale(1.02);
        }

        .video-container {
            margin-top: 10px;
            width: 100%;
            position: relative;
            overflow: hidden;
            padding-top: 56.25%; /* 16:9 aspect ratio */
            border-radius: 6px;
        }

        .video-embed {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 6px;
        }

        #search-input {
            border-radius: 4px 0 0 4px;
        }

        #search-button {
            border-radius: 0 4px 4px 0;
        }

        .loading-indicator {
            text-align: center;
            padding: 10px;
            color: #757575;
        }

        /* Mode toggle styling */
        .mode-toggle {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
        }

        .mode-toggle button {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            margin: 0 5px;
            cursor: pointer;
        }

        #surveillance-mode {
            background-color: #1565c0;
            color: white;
        }

        #pcb-mode {
            background-color: #2e7d32;
            color: white;
        }

        .mode-inactive {
            opacity: 0.6;
        }

        /* PCB specific styles */
        .pcb-card-header {
            background-color: #2e7d32 !important;
        }

        .pcb-result-item {
            border-left: 4px solid #2e7d32;
        }
        
        .defect-tag {
            display: inline-block;
            background-color: #ffcdd2;
            color: #c62828;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-right: 5px;
            margin-bottom: 5px;
        }
        
        .source-indicator {
            font-size: 10px;
            color: #666;
            text-align: right;
            padding: 2px;
            margin-top: 2px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-md-8">
                <div class="mode-toggle">
                    <button id="surveillance-mode" class="active">Surveillance Mode</button>
                    <button id="pcb-mode" class="mode-inactive">PCB Inspection Mode</button>
                </div>
                <div class="card shadow">
                    <div id="card-header" class="card-header bg-primary text-white">
                        <h3 class="mb-0">Surveillance Search Engine</h3>
                    </div>
                    <div class="card-body">
                        <div id="chat-container" class="mb-4">
                            <div id="welcome-message" class="system-message">
                                Welcome to Surveillance Search! You can ask questions like:
                                <ul>
                                    <li>Show me 'x' power line between 7PM and 8PM </li>
                                    <li>Show anomalies in UPS room 1 from last week</li>
                                    <li>Show me battery leakages over the last month</li>
                                    
                                </ul>
                            </div>
                        </div>
                        <div class="input-group">
                            <input type="text" id="search-input" class="form-control" placeholder="What would you like to search for?">
                            <button id="search-button" class="btn btn-primary">Search</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Result template (hidden) -->
    <template id="result-template">
        <div class="result-item">
            <h5 class="result-name"></h5>
            <p class="result-relevance"></p>
            <p class="result-description"></p>
            <div class="defect-tags-container"></div>
            <div class="media-container"></div>
        </div>
    </template>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const searchInput = document.getElementById('search-input');
            const searchButton = document.getElementById('search-button');
            const chatContainer = document.getElementById('chat-container');
            const resultTemplate = document.getElementById('result-template');
            const cardHeader = document.getElementById('card-header');
            const welcomeMessage = document.getElementById('welcome-message');
            const surveillanceMode = document.getElementById('surveillance-mode');
            const pcbMode = document.getElementById('pcb-mode');
            
            // Current mode
            let currentMode = "surveillance";
            
            // Mode toggle handlers
            surveillanceMode.addEventListener('click', () => {
                if (currentMode !== "surveillance") {
                    currentMode = "surveillance";
                    updateInterfaceForMode();
                    
                    // Update appearance
                    surveillanceMode.classList.remove('mode-inactive');
                    pcbMode.classList.add('mode-inactive');
                    
                    // Clear chat except welcome message
                    clearChatHistory();
                }
            });
            
            pcbMode.addEventListener('click', () => {
                if (currentMode !== "pcb") {
                    currentMode = "pcb";
                    updateInterfaceForMode();
                    
                    // Update appearance
                    pcbMode.classList.remove('mode-inactive');
                    surveillanceMode.classList.add('mode-inactive');
                    
                    // Clear chat except welcome message
                    clearChatHistory();
                }
            });
            
            // Update interface based on mode
            function updateInterfaceForMode() {
                if (currentMode === "surveillance") {
                    // Update header
                    cardHeader.className = "card-header bg-primary text-white";
                    cardHeader.querySelector('h3').textContent = "Surveillance Search Engine";
                    
                    // Update button color
                    searchButton.className = "btn btn-primary";
                    
                    // Update welcome message
                    welcomeMessage.className = "system-message";
                    welcomeMessage.innerHTML = `
                        Welcome to Surveillance Search! You can ask questions like:
                        <ul>
                            <li>Find a person in a black t-shirt</li>
                            <li>Show me clips with people running</li>
                            <li>Show me footage from yesterday afternoon</li>
                            <li>Find groups of people in the lobby from last week</li>
                        </ul>
                    `;
                    
                    // Update search placeholder
                    searchInput.placeholder = "What would you like to search for?";
                } else {
                    // Update header
                    cardHeader.className = "card-header pcb-card-header text-white";
                    cardHeader.querySelector('h3').textContent = "PCB Inspection Search Engine";
                    
                    // Update button color
                    searchButton.className = "btn btn-success";
                    
                    // Update welcome message
                    welcomeMessage.className = "pcb-system-message";
                    welcomeMessage.innerHTML = `
                        Welcome to PCB Inspection Search! You can ask questions like:
                        <ul>
                            <li>Find PCBs with missing capacitors</li>
                            <li>Show boards with solder bridge defects</li>
                            <li>Find cold solder joints from yesterday</li>
                            <li>Show PCBs with misaligned components</li>
                        </ul>
                    `;
                    
                    // Update search placeholder
                    searchInput.placeholder = "Describe the PCB defect to search for...";
                }
            }
            
            // Clear chat history but keep welcome message
            function clearChatHistory() {
                // Remove all children except the welcome message
                while (chatContainer.childNodes.length > 1) {
                    chatContainer.removeChild(chatContainer.lastChild);
                }
            }

            // Function to add a message to the chat
            function addMessage(text, className) {
                const messageDiv = document.createElement('div');
                messageDiv.className = className;
                messageDiv.textContent = text;
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            // Function to add loading indicator
            function addLoadingIndicator() {
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'loading-indicator';
                loadingDiv.id = 'loading';
                loadingDiv.textContent = 'Searching...';
                chatContainer.appendChild(loadingDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            // Function to remove loading indicator
            function removeLoadingIndicator() {
                const loadingDiv = document.getElementById('loading');
                if (loadingDiv) {
                    loadingDiv.remove();
                }
            }

            // Function to extract possible defect tags from description
            function extractDefectTags(description) {
                const defectKeywords = [
                    "missing component", "solder bridge", "cold solder", "misaligned",
                    "crack", "short circuit", "open circuit", "lifted pad", "tombstoning",
                    "overheating", "damaged", "incorrect component", "wrong orientation",
                    "flux residue", "insufficient solder", "excessive solder"
                ];
                
                const foundDefects = [];
                const lowerDesc = description.toLowerCase();
                
                defectKeywords.forEach(keyword => {
                    if (lowerDesc.includes(keyword.toLowerCase())) {
                        foundDefects.push(keyword);
                    }
                });
                
                return foundDefects;
            }

            // Function to check if URL is an image
            function isImageUrl(url) {
                // Handle both data URLs and regular URLs
                if (url.startsWith('data:image/')) {
                    return true;
                }
                
                // Handle HTTP/HTTPS URLs
                if (url.startsWith('http')) {
                    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'];
                    const lowerCaseUrl = url.toLowerCase();
                    return imageExtensions.some(ext => lowerCaseUrl.endsWith(ext)) || 
                           lowerCaseUrl.includes('/image') ||
                           lowerCaseUrl.includes('supabase.co'); // Include your Supabase storage URLs
                }
                
                return false;
            }

            // Function to check if URL is a video
            function isVideoUrl(url) {
                if (!url || typeof url !== 'string') return false;
                
                const videoExtensions = ['.mp4', '.webm', '.ogg', '.mov', '.avi'];
                const videoServices = ['youtube.com', 'youtu.be', 'vimeo.com'];
                
                const lowerCaseUrl = url.toLowerCase();
                
                // Check for file extensions
                if (videoExtensions.some(ext => lowerCaseUrl.endsWith(ext))) {
                    return true;
                }
                
                // Check for video service domains
                if (videoServices.some(service => lowerCaseUrl.includes(service))) {
                    return true;
                }
                
                return false;
            }

            // Function to add debug indicator for image sources
            function addDebugIndicator(resultDiv, url) {
                // Create a small indicator showing what type of image source is being used
                const indicatorDiv = document.createElement('div');
                indicatorDiv.className = 'source-indicator';
                
                if (url && url.startsWith('data:image/')) {
                    indicatorDiv.textContent = '🔒 Base64 Image';
                    indicatorDiv.style.color = '#0066cc';
                } else if (url && url.startsWith('http')) {
                    indicatorDiv.textContent = '🔗 URL Image';
                    indicatorDiv.style.color = '#009900';
                } else {
                    indicatorDiv.textContent = '❓ Unknown Source';
                    indicatorDiv.style.color = '#cc0000';
                }
                
                // Add the indicator to the result div
                resultDiv.querySelector('.media-container').appendChild(indicatorDiv);
            }

            // Function to create appropriate media element
            function createMediaElement(url) {
                if (!url) {
                    // Handle missing URL
                    const container = document.createElement('div');
                    container.className = 'image-container';
                    
                    const img = document.createElement('img');
                    img.className = 'result-image';
                    img.src = 'https://via.placeholder.com/400x300?text=No+Image+Available';
                    img.alt = 'No image available';
                    
                    container.appendChild(img);
                    return container;
                }
                
                if (isImageUrl(url)) {
                    // Create image container
                    const container = document.createElement('div');
                    container.className = 'image-container';
                    
                    // Create image element
                    const img = document.createElement('img');
                    img.className = 'result-image';
                    img.src = url;
                    img.alt = 'Result image';
                    img.onerror = function() {
                        this.onerror = null;
                        this.src = 'https://via.placeholder.com/400x300?text=Image+Load+Error';
                    };
                    
                    container.appendChild(img);
                    return container;
                } else if (isVideoUrl(url)) {
                    // For simplicity, treat as generic video link
                    const container = document.createElement('div');
                    container.className = 'video-container';
                    
                    // Create iframe for video embedding (simplified)
                    const iframe = document.createElement('iframe');
                    iframe.className = 'video-embed';
                    iframe.src = url;
                    iframe.allowFullscreen = true;
                    
                    container.appendChild(iframe);
                    return container;
                } else {
                    // For other media types, provide a direct link
                    const container = document.createElement('div');
                    container.className = 'image-container';
                    
                    // Create a link with a placeholder image
                    const link = document.createElement('a');
                    link.href = url;
                    link.target = '_blank';
                    
                    const img = document.createElement('img');
                    img.className = 'result-image';
                    img.src = 'https://via.placeholder.com/400x200?text=View+Media';
                    img.alt = 'Click to view content';
                    
                    link.appendChild(img);
                    container.appendChild(link);
                    return container;
                }
            }

            // Function to display search results
            function displayResults(results) {
                const aiMessage = document.createElement('div');
                aiMessage.className = 'ai-message';
                
                if (results.length === 0) {
                    aiMessage.textContent = 'No matching results found. Try a different search.';
                    chatContainer.appendChild(aiMessage);
                    return;
                }

                aiMessage.textContent = `Found ${results.length} relevant results:`;
                chatContainer.appendChild(aiMessage);

                // Display each result
                results.forEach(result => {
                    const resultDiv = document.importNode(resultTemplate.content, true);
                    const resultName = resultDiv.querySelector('.result-name');
                    
                    // Apply mode-specific styling
                    if (currentMode === "pcb") {
                        resultName.className = "pcb-result-name";
                        resultDiv.querySelector('.result-item').classList.add('pcb-result-item');
                    }
                    
                    resultName.textContent = result.name;
                    resultDiv.querySelector('.result-relevance').textContent = `Relevance: ${result.relevance}`;
                    resultDiv.querySelector('.result-description').textContent = result.description;
                    
                    // Add defect tags for PCB mode
                    if (currentMode === "pcb") {
                        const defectTagsContainer = resultDiv.querySelector('.defect-tags-container');
                        const defects = extractDefectTags(result.description);
                        
                        if (defects.length > 0) {
                            defects.forEach(defect => {
                                const tag = document.createElement('span');
                                tag.className = 'defect-tag';
                                tag.textContent = defect;
                                defectTagsContainer.appendChild(tag);
                            });
                        }
                    }

                    if (result.time_stamp) {
                        const timestamp = new Date(result.time_stamp);
                        const timestampElement = document.createElement('p');
                        timestampElement.className = 'result-timestamp';
                        timestampElement.textContent = `Recorded: ${timestamp.toLocaleString()}`;
                        resultDiv.querySelector('.result-description').after(timestampElement);
                    }
                    
                    const mediaContainer = resultDiv.querySelector('.media-container');
                    const mediaElement = createMediaElement(result.url);
                    mediaContainer.appendChild(mediaElement);
                    
                    // Add debug indicator
                    addDebugIndicator(resultDiv, result.url);
                    
                    chatContainer.appendChild(resultDiv);
                });

                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            // Function to perform search
            async function performSearch(query) {
                if (!query.trim()) return;

                // Add user message
                addMessage(query, 'user-message');
                
                // Show loading indicator
                addLoadingIndicator();

                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ 
                            query: query,
                            mode: currentMode
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Search request failed');
                    }

                    const data = await response.json();
                    
                    // Remove loading indicator
                    removeLoadingIndicator();
                    
                    // Display results
                    displayResults(data.results);
                } catch (error) {
                    console.error('Error:', error);
                    removeLoadingIndicator();
                    addMessage('Sorry, there was an error processing your search. Please try again.', 'ai-message');
                }
            }

            // Event listeners
            searchButton.addEventListener('click', () => {
                const query = searchInput.value;
                performSearch(query);
                searchInput.value = '';
            });

            searchInput.addEventListener('keypress', (event) => {
                if (event.key === 'Enter') {
                    const query = searchInput.value;
                    performSearch(query);
                    searchInput.value = '';
                }
            });

            // Focus input on page load
            searchInput.focus();
        });
    </script>
</body>
</html>
"""

# Route for the home page
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(content=HTML_CONTENT)


@app.get("/api/image/{clip_id}")
async def get_image(clip_id: str):
    # Get the specific image from database
    db_connector = SupabaseConnector()
    response = db_connector.client.table("todos").select("base_64_image").eq("id", clip_id).execute()
    
    if not response.data:
        return HTTPException(status_code=404, detail="Image not found")
    
    base64_data = response.data[0]["base_64_image"]
    
    # Check if it's a URL
    if base64_data.startswith(('http://', 'https://')):
        # Redirect to the actual URL
        return Response(
            status_code=307,  # Temporary redirect
            headers={"Location": base64_data}
        )
    
    # If base64 includes a data URI prefix, remove it
    if "," in base64_data:
        _, base64_data = base64_data.split(",", 1)
    
    # Decode the base64 data
    try:
        image_data = base64.b64decode(base64_data)
        return Response(content=image_data, media_type="image/jpeg")
    except Exception as e:
        print(f"Error decoding image: {e}")
        return HTTPException(status_code=500, detail="Error processing image")

# API endpoint 
@app.post("/api/search")
async def search(query: SearchQuery):
    # Modify search to include mode
    print(f"Processing search in {query.mode} mode: '{query.query}'")

    # Add contextual enhancement to query based on mode
    enhanced_query = query.query
    if query.mode == "pcb":
        # Add PCB context to the query
        enhanced_query = f"PCB inspection: {query.query}"
    
    # Use the search engine with the enhanced query
    results = search_engine.search(enhanced_query)
    
    # Format the results
    formatted_results = []
    for clip in results:
        relevance = clip.get("relevance_score", 0) * 100
        base64_data = clip.get("base_64_image", "")

        # Check if the base_64_image field contains a URL or Base64 data
        if base64_data:
            # Check if it's a URL (starts with http)
            if base64_data.startswith(('http://', 'https://')):
                img_actual = base64_data  # Use the URL directly
                print(f"Using URL directly: {img_actual[:50]}...")
            else:
                # Handle as Base64 data
                if "," in base64_data:
                    _, base64_data = base64_data.split(",", 1)
                img_actual = f"data:image/jpeg;base64,{base64_data}"
                print("Using Base64 data")
        else:
            # Fallback if no image data
            img_actual = ""
        
        # Customize display name based on mode
        display_name = clip['camera_id']
        if query.mode == "pcb":
            # For PCB mode, use a more appropriate name format
            display_name = f"PCB-{clip['id']}"
        
        # Add the timestamp to the response
        formatted_result = {
            "name": display_name,
            "url": img_actual,
            "description": clip['image_description'],
            "relevance": f"{relevance:.1f}%",
            "time_stamp": clip.get('time_created') 
        }
        formatted_results.append(formatted_result)
    
    print(f"API returning {len(formatted_results)} results to frontend")
    if formatted_results:
        print(f"First result: {formatted_results[0]['name']}")
    
    return {"results": formatted_results}

# http://localhost:8000/
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)