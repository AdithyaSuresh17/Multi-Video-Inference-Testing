# example_usage.py
from search_engine import ClipSearchEngine

def run_example_search(query):
    """Run an example search and print the results"""
    print(f"\nSearching for: '{query}'")
    print("-" * 50)
    
    engine = ClipSearchEngine()
    results = engine.search(query)
    
    print("\nResults:")
    if not results:
        print("No matching clips found.")
    else:
        for i, clip in enumerate(results, 1):
            relevance = clip.get("relevance_score", 0) * 100
            print(f"\n{i}. {clip['Clip_Name']} (Relevance: {relevance:.1f}%)")
            print(f"   URL: {clip['Clip_URL']}")
            print(f"   Description: {clip['Clip_Description']}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    # Example searches to test the system
    example_queries = [
        "Find the person in black t-shirt",
        "Show me people sitting in their bed",
        "Find clips with a wall behind the person"
    ]
    
    for query in example_queries:
        run_example_search(query)