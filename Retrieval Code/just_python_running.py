# main.py
from search import ClipSearchEngine

def format_results(results):
    """Format search results for display"""
    if not results:
        return "No matching clips found."
    
    output = f"Found {len(results)} relevant clips:\n\n"
    
    for i, clip in enumerate(results, 1):
        relevance = clip.get("relevance_score", 0) * 100
        output += f"{i}. {clip['Clip_Name']} (Relevance: {relevance:.1f}%)\n"
        output += f"   URL: {clip['Clip_URL']}\n"
        output += f"   Description: {clip['Clip_Description']}\n\n"
    
    return output

def main():
    """Main function to run the clip search"""
    search_engine = ClipSearchEngine()
    
    print("Clip Search System")
    print("------------------")
    print("Type 'exit' to quit\n")
    
    while True:
        query = input("What would you like to search for? ")
        
        if query.lower() in ['exit', 'quit', 'q']:
            break
        
        if not query.strip():
            continue
        
        results = search_engine.search(query)
        
        print("\n" + "="*60)
        print(format_results(results))
        print("="*60 + "\n")

if __name__ == "__main__":
    main()