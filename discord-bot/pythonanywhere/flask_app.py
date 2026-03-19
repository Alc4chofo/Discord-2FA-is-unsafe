from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ============================================
# CONFIGURATION - Replace with your values
# ============================================
BOT_TOKEN = 'yourtokenhere'
GUILD_ID = 'theguildidhere'
VERIFIED_ROLE_NAME = 'Verified'

# Discord API base URL
DISCORD_API = 'https://discord.com/api/v10'

# Headers for Discord API requests
def get_headers():
    return {
        'Authorization': f'Bot {BOT_TOKEN}',
        'Content-Type': 'application/json'
    }

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_role_id_by_name(guild_id, role_name):
    """Get role ID by role name"""
    url = f'{DISCORD_API}/guilds/{guild_id}/roles'
    response = requests.get(url, headers=get_headers())
    
    if response.status_code == 200:
        roles = response.json()
        for role in roles:
            if role['name'] == role_name:
                return role['id']
    return None

def add_role_to_member(guild_id, user_id, role_id):
    """Add a role to a guild member"""
    url = f'{DISCORD_API}/guilds/{guild_id}/members/{user_id}/roles/{role_id}'
    response = requests.put(url, headers=get_headers())
    return response.status_code == 204

def get_member_info(guild_id, user_id):
    """Get member information"""
    url = f'{DISCORD_API}/guilds/{guild_id}/members/{user_id}'
    response = requests.get(url, headers=get_headers())
    
    if response.status_code == 200:
        return response.json()
    return None

def send_log_message(channel_id, embed):
    """Send a message to a channel"""
    url = f'{DISCORD_API}/channels/{channel_id}/messages'
    payload = {'embeds': [embed]}
    response = requests.post(url, headers=get_headers(), json=payload)
    return response.status_code == 200

# ============================================
# ROUTES
# ============================================

@app.route('/')
def home():
    return jsonify({
        'status': 'VerifiKat verification server is running',
        'endpoints': {
            '/verify': 'POST - Verify a user',
            '/health': 'GET - Health check'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/verify', methods=['POST'])
def verify_user():
    """
    Verify a user and assign them the Verified role.
    
    Expected JSON body:
    {
        "discordUserId": "123456789012345678",
        "discordUsername": "optional_username"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    discord_user_id = data.get('discordUserId')
    discord_username = data.get('discordUsername', 'Unknown')
    
    if not discord_user_id:
        return jsonify({'error': 'Missing discordUserId'}), 400
    
    # Get the Verified role ID
    role_id = get_role_id_by_name(GUILD_ID, VERIFIED_ROLE_NAME)
    
    if not role_id:
        return jsonify({'error': f'Role "{VERIFIED_ROLE_NAME}" not found'}), 404
    
    # Check if user is in the guild
    member = get_member_info(GUILD_ID, discord_user_id)
    
    if not member:
        return jsonify({'error': 'User not found in server'}), 404
    
    # Add the role to the user
    success = add_role_to_member(GUILD_ID, discord_user_id, role_id)
    
    if success:
        username = member.get('user', {}).get('username', discord_username)
        print(f'✅ Verified user: {username} ({discord_user_id})')
        
        return jsonify({
            'success': True,
            'message': f'User {username} verified successfully'
        })
    else:
        return jsonify({'error': 'Failed to assign role'}), 500

# ============================================
# FOR LOCAL TESTING ONLY
# ============================================
if __name__ == '__main__':
    app.run(debug=True)
