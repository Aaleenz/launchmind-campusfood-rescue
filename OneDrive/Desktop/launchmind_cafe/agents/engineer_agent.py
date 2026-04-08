import os
import json
import base64
import requests
from groq import Groq
from message_bus import message_bus

class EngineerAgent:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found!")
        
        self.client = Groq(api_key=api_key)
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.repo_name = "Aaleenz/launchmind-campusfood-rescue"  # Your repo
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github+json"
        }
    
    def generate_landing_page(self, product_spec: dict) -> str:
        prompt = f"""
        Create a complete HTML landing page for CampusFood Rescue based on this product spec:
        
        {json.dumps(product_spec, indent=2)}
        
        The landing page must include:
        - Hero section with headline and tagline
        - Features section (show the top 3 features)
        - How it works section
        - Call-to-action button (email signup or SMS alert signup)
        - Responsive design with modern CSS
        - Mobile-friendly
        
        Return ONLY the complete HTML/CSS code (no explanations).
        """
        
        print("🔧 ENGINEER: Generating HTML landing page...")
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        
        html = response.choices[0].message.content
        # Clean up markdown code blocks if present
        if html.startswith("```html"):
            html = html[7:]
        if html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        
        return html.strip()
    
    def create_github_issue(self, product_spec: dict) -> str:
        url = f"https://api.github.com/repos/{self.repo_name}/issues"
        
        issue_data = {
            "title": "Initial Landing Page - CampusFood Rescue",
            "body": f"""
## Product Specification Summary
**Value Proposition:** {product_spec.get('value_proposition', 'N/A')}

**Top Features:**
{chr(10).join([f"- {f['name']}: {f['description']}" for f in product_spec.get('features', [])[:3]])}

**Target Personas:**
{chr(10).join([f"- {p['name']} ({p['role']}): {p['pain_point']}" for p in product_spec.get('personas', [])])}

## Engineer Task
Build a responsive landing page showcasing the product with signup functionality.
            """,
            "labels": ["enhancement", "landing-page"]
        }
        
        response = requests.post(url, headers=self.headers, json=issue_data)
        if response.status_code == 201:
            return response.json()["html_url"]
        else:
            print(f"   ❌ Failed to create issue: {response.status_code}")
            return None
    
    def get_main_branch_sha(self) -> str:
        """Get the SHA of the main branch"""
        url = f"https://api.github.com/repos/{self.repo_name}/git/refs/heads/main"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()["object"]["sha"]
        else:
            raise Exception(f"Failed to get main branch: {response.status_code}")
    
    def delete_branch_if_exists(self, branch_name: str):
        """Delete branch if it already exists"""
        url = f"https://api.github.com/repos/{self.repo_name}/git/refs/heads/{branch_name}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            print(f"   Deleted existing branch: {branch_name}")
        elif response.status_code == 404:
            pass  # Branch doesn't exist, that's fine
        else:
            print(f"   Branch check: {response.status_code}")
    
    def create_branch(self, branch_name: str, base_sha: str) -> bool:
        """Create a new branch"""
        url = f"https://api.github.com/repos/{self.repo_name}/git/refs"
        branch_data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
        response = requests.post(url, headers=self.headers, json=branch_data)
        if response.status_code == 201:
            print(f"   ✅ Branch created: {branch_name}")
            return True
        else:
            print(f"   ❌ Failed to create branch: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def commit_file(self, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
        """Commit a file to the branch"""
        url = f"https://api.github.com/repos/{self.repo_name}/contents/{file_path}"
        content_encoded = base64.b64encode(content.encode()).decode()
        
        commit_data = {
            "message": commit_message,
            "content": content_encoded,
            "branch": branch_name,
            "committer": {
                "name": "EngineerAgent",
                "email": "agent@launchmind.ai"
            }
        }
        
        response = requests.put(url, headers=self.headers, json=commit_data)
        if response.status_code in [200, 201]:
            print(f"   ✅ File committed: {file_path}")
            return True
        else:
            print(f"   ❌ Failed to commit: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def create_pull_request(self, branch_name: str, title: str, body: str) -> tuple:
        """Create a pull request"""
        url = f"https://api.github.com/repos/{self.repo_name}/pulls"
        pr_data = {
            "title": title,
            "body": body,
            "head": branch_name,
            "base": "main"
        }
        
        response = requests.post(url, headers=self.headers, json=pr_data)
        if response.status_code == 201:
            pr_info = response.json()
            return pr_info["html_url"], pr_info["number"]
        else:
            print(f"   ❌ Failed to create PR: {response.status_code}")
            print(f"   Response: {response.text}")
            return None, None
    
    def run(self):
        print("\n🔧 ENGINEER AGENT: Waiting for task...")
        
        while True:
            msg = message_bus.receive("engineer")
            if msg and msg["message_type"] == "task":
                print(f"\n🔧 ENGINEER AGENT: Received task to build landing page")
                
                product_spec = msg["payload"].get("product_spec", {})
                
                # Generate HTML landing page
                html = self.generate_landing_page(product_spec)
                
                # Create GitHub issue
                print("🔧 ENGINEER: Creating GitHub issue...")
                issue_url = self.create_github_issue(product_spec)
                if issue_url:
                    print(f"   ✅ Issue created: {issue_url}")
                
                # Setup branch
                branch_name = f"agent-landing-page-{int(os.timestamp()) if hasattr(os, 'timestamp') else 123}" 
                # Use timestamp to make branch unique
                import time
                branch_name = f"agent-landing-page-{int(time.time())}"
                
                try:
                    # Get main branch SHA
                    main_sha = self.get_main_branch_sha()
                    
                    # Delete branch if it exists (cleanup)
                    self.delete_branch_if_exists(branch_name)
                    
                    # Create new branch
                    if not self.create_branch(branch_name, main_sha):
                        raise Exception("Failed to create branch")
                    
                    # Commit HTML file
                    if not self.commit_file(branch_name, "index.html", html, "Add landing page for CampusFood Rescue"):
                        raise Exception("Failed to commit file")
                    
                    # Create PR
                    pr_title = "🚀 Initial Landing Page - CampusFood Rescue"
                    pr_body = f"""
## What's in this PR?
- Complete landing page for CampusFood Rescue
- Responsive design
- Features section showcasing the product
- Call-to-action for signups

## Product Spec Implemented
- Value prop: {product_spec.get('value_proposition', 'N/A')[:100]}

## Next Steps
- Add backend API integration
- Implement SMS notification system
- Add cafeteria dashboard
                    """
                    
                    pr_url, pr_number = self.create_pull_request(branch_name, pr_title, pr_body)
                    
                    if pr_url:
                        print(f"   ✅ PR opened: {pr_url}")
                        
                        # Send results back to CEO
                        result = {
                            "pr_url": pr_url,
                            "issue_url": issue_url,
                            "branch": branch_name,
                            "pr_number": pr_number,
                            "status": "success"
                        }
                        
                        message_bus.send("engineer", "ceo", "result", result, msg["message_id"])
                        print(f"🔧 ENGINEER AGENT: Sent results to CEO")
                    else:
                        raise Exception("Failed to create PR")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    # Send failure result
                    result = {
                        "pr_url": None,
                        "issue_url": issue_url,
                        "status": "failed",
                        "error": str(e)
                    }
                    message_bus.send("engineer", "ceo", "result", result, msg["message_id"])
                
                break