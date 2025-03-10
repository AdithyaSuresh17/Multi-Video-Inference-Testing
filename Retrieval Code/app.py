# app.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from search import ClipSearchEngine
import uvicorn

# Create FastAPI app
app = FastAPI(title="Clip Search Engine")

# Initialize search engine
search_engine = ClipSearchEngine()

# Model for search query
class SearchQuery(BaseModel):
    query: str

# HTML content
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clip Search</title>
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
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h3 class="mb-0">Clip Search Engine</h3>
                    </div>
                    <div class="card-body">
                        <div id="chat-container" class="mb-4">
                            <div class="system-message">
                                Welcome to Clip Search! Ask me to find clips, for example: "Find a person in a black t-shirt" or "Show me clips with dogs playing".
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
            <div class="media-container"></div>
        </div>
    </template>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const searchInput = document.getElementById('search-input');
            const searchButton = document.getElementById('search-button');
            const chatContainer = document.getElementById('chat-container');
            const resultTemplate = document.getElementById('result-template');

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

            // Function to check if URL is an image
            function isImageUrl(url) {
                const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'];
                const lowerCaseUrl = url.toLowerCase();
                return imageExtensions.some(ext => lowerCaseUrl.endsWith(ext));
            }

            // Function to check if URL is a video
            function isVideoUrl(url) {
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

            // Function to create appropriate media element
            function createMediaElement(url) {
                if (isImageUrl(url)) {
                    // Create image container
                    const container = document.createElement('div');
                    container.className = 'image-container';
                    
                    // Create image element
                    const img = document.createElement('img');
                    img.className = 'result-image';
                    img.src = url;
                    img.alt = 'Clip result';
                    img.onerror = function() {
                        this.onerror = null;
                        this.src = 'https://via.placeholder.com/400x300?text=Image+Not+Available';
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
                    aiMessage.textContent = 'No matching clips found. Try a different search.';
                    chatContainer.appendChild(aiMessage);
                    return;
                }

                aiMessage.textContent = `Found ${results.length} relevant clips:`;
                chatContainer.appendChild(aiMessage);

                // Display each result
                results.forEach(result => {
                    const resultDiv = document.importNode(resultTemplate.content, true);
                    
                    resultDiv.querySelector('.result-name').textContent = result.name;
                    resultDiv.querySelector('.result-relevance').textContent = `Relevance: ${result.relevance}`;
                    resultDiv.querySelector('.result-description').textContent = result.description;
                    
                    const mediaContainer = resultDiv.querySelector('.media-container');
                    const mediaElement = createMediaElement(result.url);
                    mediaContainer.appendChild(mediaElement);
                    
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
                        body: JSON.stringify({ query })
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

# API endpoint for search
@app.post("/api/search")
async def search(query: SearchQuery):
    results = search_engine.search(query.query)
    
    # Format the results
    formatted_results = []
    for clip in results:
        relevance = clip.get("relevance_score", 0) * 100
        formatted_results.append({
            "name": clip['Clip_Name'],
            "url": clip['Clip_URL'],
            "description": clip['Clip_Description'],
            "relevance": f"{relevance:.1f}%"
        })
    
    return {"results": formatted_results}

# Run the app
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
