#!/usr/bin/env python3
"""
LaunchMind Cafe - Multi-Agent System for CampusFood Rescue
Run: python main.py
"""

import sys
import time
import threading
from agents.ceo_agent import CEOAgent
from agents.product_agent import ProductAgent
from agents.engineer_agent import EngineerAgent
from agents.marketing_agent import MarketingAgent
from agents.qa_agent import QAAgent
from message_bus import message_bus
from dotenv import load_dotenv

load_dotenv()

def run_agent(agent_instance, agent_name):
    """Run an agent and handle errors"""
    try:
        agent_instance.run()
    except Exception as e:
        print(f"❌ {agent_name} crashed: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     🚀 LAUNCHMIND CAFE - Multi-Agent System             ║
    ║     CampusFood Rescue: Real-time food waste alerts      ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Your startup idea
    STARTUP_IDEA = """
    CampusFood Rescue - A real-time notification system for leftover campus cafeteria food 
    that would otherwise be thrown away. Students get SMS alerts when food is available 
    at discounted prices. Cafeteria managers get analytics on waste reduction.
    """
    
    print(f"📋 Startup Idea: {STARTUP_IDEA.strip()}\n")
    print("🤖 Initializing Multi-Agent System...\n")
    
    # Create agent instances
    ceo = CEOAgent()
    product = ProductAgent()
    engineer = EngineerAgent()
    marketing = MarketingAgent()
    qa = QAAgent(ceo.client, message_bus)  # Pass Groq client and message bus
    
    # Run agents in threads (so they can all listen to message bus)
    threads = []
    
    # Start product, engineer, marketing, QA agents first (they'll wait for messages)
    for agent, name in [(product, "Product"), (engineer, "Engineer"), (marketing, "Marketing"), (qa, "QA")]:
        t = threading.Thread(target=run_agent, args=(agent, name))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.5)  # Give each agent time to start
    
    # Give agents time to start up
    time.sleep(2)
    
    # Run CEO (this will orchestrate everything)
    try:
        results = ceo.run(STARTUP_IDEA)
        
        print("\n" + "="*60)
        print("🎉 SYSTEM EXECUTION COMPLETE!")
        print("="*60)
        print("\n📊 Final Results:")
        print(f"   • Product Spec: Created with {len(results.get('product_spec', {}).get('features', []))} features")
        print(f"   • GitHub PR: {results.get('engineer_result', {}).get('pr_url', 'N/A')}")
        print(f"   • Email: Sent to test inbox")
        print(f"   • Social Posts: {len(results.get('marketing_result', {}).get('social_posts', []))} generated")
        print(f"   • Slack: Posted to #launches channel")
        
        # QA results
        if results.get('qa_results'):
            qa = results['qa_results']
            print(f"\n🔍 QA Review Results:")
            print(f"   • Verdict: {qa.get('verdict', 'N/A')}")
            print(f"   • Overall Score: {qa.get('overall_score', 'N/A')}/10")
            print(f"   • QA Iterations: {qa.get('qa_iterations', 0)}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ System interrupted by user")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        import traceback
        traceback.print_exc()
    
    # Give threads time to complete
    print("\n⏳ Waiting for final Slack post to complete...")
    time.sleep(5)
    
    print("\n💡 Check your:")
    print("   • GitHub repository for the new PR")
    print("   • Slack #launches channel for the announcement")
    print("   • Email inbox for the cold outreach")
    print("\n✅ Done!\n")

if __name__ == "__main__":
    main()