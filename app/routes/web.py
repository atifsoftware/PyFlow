"""
app/routes/web.py
=====================
পাবলিক ওয়েব রাউট (হোম, ডক্স, ইত্যাদি)
"""

from core.controller import action


def register_web_routes(router):
    """পাবলিক ওয়েব রাউট রেজিস্টার করে।"""
    
    from app.controllers.home_controller import HomeController
    
    # হোম পেজ
    router.get("/", action(HomeController, "index"), name="home")
    
    # ডকুমেন্টেশন পেজ
    router.get("/docs", action(HomeController, "docs"), name="docs")
    
    # API Documentation UI (Swagger-like)
    router.get("/api-docs", lambda req, sess: __import__("core.response", fromlist=["Response"]).Response.html("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyFlow API Documentation</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .endpoint { background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; border-radius: 4px; }
        .method { display: inline-block; padding: 4px 8px; border-radius: 3px; font-weight: bold; font-size: 12px; margin-right: 10px; }
        .get { background: #61affe; color: white; }
        .post { background: #49cc90; color: white; }
        .put { background: #fca130; color: white; }
        .delete { background: #f93e3e; color: white; }
        .path { font-family: 'Courier New', monospace; font-size: 16px; color: #2c3e50; }
        .description { color: #7f8c8d; margin: 10px 0; }
        .tag { background: #e1e8ed; color: #5c7080; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px; }
        .security { background: #fff3cd; color: #856404; padding: 10px; border-radius: 4px; margin-top: 10px; font-size: 13px; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
        .try-it { background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-top: 10px; }
        .try-it:hover { background: #2980b9; }
        .response { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 4px; margin-top: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 PyFlow API Documentation</h1>
        <p>Welcome to the PyFlow API documentation. This API provides endpoints for authentication, user management, and more.</p>
        
        <h2>Authentication Endpoints</h2>
        <div class="endpoint">
            <span class="method post">POST</span>
            <span class="path">/api/login</span>
            <span class="tag">Authentication</span>
            <p class="description">User login endpoint. Send username and password to receive a JWT token.</p>
            <p><strong>Request Body:</strong></p>
            <code>{"username": "string", "password": "string"}</code>
        </div>
        
        <h2>User Endpoints</h2>
        <div class="endpoint">
            <span class="method get">GET</span>
            <span class="path">/api/v1/profile</span>
            <span class="tag">User</span>
            <p class="description">Get current authenticated user's profile information.</p>
            <div class="security">🔒 Requires Authentication: Bearer Token</div>
        </div>
        
        <h2>Admin Endpoints</h2>
        <div class="endpoint">
            <span class="method get">GET</span>
            <span class="path">/api/v1/users</span>
            <span class="tag">Admin</span>
            <p class="description">List all users in the system.</p>
            <div class="security">🔒 Requires Authentication: Bearer Token + Admin Role</div>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <span class="path">/api/v1/users</span>
            <span class="tag">Admin</span>
            <p class="description">Create a new user.</p>
            <p><strong>Request Body:</strong></p>
            <code>{"name": "string", "email": "string", "password": "string"}</code>
            <div class="security">🔒 Requires Authentication: Bearer Token + Admin Role</div>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <span class="path">/api/v1/users/{id}</span>
            <span class="tag">Admin</span>
            <p class="description">Get a specific user by ID.</p>
            <div class="security">🔒 Requires Authentication: Bearer Token + Admin Role</div>
        </div>
        
        <div class="endpoint">
            <span class="method put">PUT</span>
            <span class="path">/api/v1/users/{id}</span>
            <span class="tag">Admin</span>
            <p class="description">Update an existing user.</p>
            <div class="security">🔒 Requires Authentication: Bearer Token + Admin Role</div>
        </div>
        
        <div class="endpoint">
            <span class="method delete">DELETE</span>
            <span class="path">/api/v1/users/{id}</span>
            <span class="tag">Admin</span>
            <p class="description">Delete a user.</p>
            <div class="security">🔒 Requires Authentication: Bearer Token + Admin Role</div>
        </div>
        
        <h2>Utility Endpoints</h2>
        <div class="endpoint">
            <span class="method get">GET</span>
            <span class="path">/api/version</span>
            <span class="tag">System</span>
            <p class="description">Get API version information.</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <span class="path">/api/docs</span>
            <span class="tag">System</span>
            <p class="description">Get this API documentation in JSON format (OpenAPI 3.0).</p>
        </div>
        
        <hr style="margin: 40px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #7f8c8d; font-size: 14px;">Generated by PyFlow Framework • OpenAPI 3.0 Specification</p>
    </div>
</body>
</html>
    """), name="api.docs.ui")
