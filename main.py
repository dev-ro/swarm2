from kernel import MasterAgent, knowledge_base

def main():
    print("Initializing SOAE Kernel (MasterAgent)...")
    master_kernel = MasterAgent()
    
    print("Welcome to AutoSwarm! Type 'exit' to quit.\n")
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            
            if not user_input.strip():
                continue
                
            master_kernel.print_response(user_input, stream=True)
            print() # Add an empty line for readability
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
