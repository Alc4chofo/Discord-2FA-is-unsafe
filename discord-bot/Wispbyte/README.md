# How to set up the discord bot and its features:

## Features

- ✅ Creates a "Verified" role automatically (if it doesn't exist)
- ✅ Creates an admin role for the bot
- ✅ Sends a verification embed with button to the phis website
- ✅ Webhook endpoint for your website to call when verification completes
- ✅ Logs phis to a private channel

## Setup

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Copy the **Bot Token** (you'll need this)
5. Enable these **Privileged Gateway Intents**:
   - Server Members Intent
   - Message Content Intent

### 2. Invite the Bot

1. Go to the "OAuth2" > "URL Generator" tab
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Manage Roles
   - Manage Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - View Channels
4. Copy the generated URL and open it to invite the bot

### 3. Configure the Bot

Edit `bot.js` and update the `CONFIG` object:

```javascript
const CONFIG = {
    BOT_TOKEN: 'your-bot-token-here',
    VERIFICATION_WEBSITE_URL: 'https://your-verification-site.com',
    VERIFICATION_CHANNEL_NAME: 'verify',      // Channel where verify message is sent
    LOG_CHANNEL_NAME: 'verification-logs',    // Channel for verification logs
    VERIFIED_ROLE_NAME: 'Verified',           // Role given to verified users
    BOT_ROLE_NAME: 'Verification Bot',        // Admin role for the bot
    WEBHOOK_PORT: 3000                        // Port for the webhook server
};
```

### 4. Create the Verify Channel

Create a channel called `verify` (or whatever you set in `VERIFICATION_CHANNEL_NAME`) in your Discord server. The bot will send the verification message there.

### 5. Install & Run

```bash
npm install
npm start
```

## Webhook API

Your verification website should call this endpoint when a user completes verification:

### POST `/verify`

**Request Body:**
```json
{
    "discordUserId": "123456789012345678",
    "discordUsername": "username#1234",
    "guildId": "987654321098765432"
}
```

**Response (Success):**
```json
{
    "success": true,
    "message": "User username#1234 verified successfully"
}
```

**Response (Error):**
```json
{
    "error": "Error message here"
}
```

### GET `/health`

Health check endpoint that returns bot status.

## How It Works

1. User joins the Discord server
2. User sees the verification message in `#verify` channel
3. User clicks the "Verify" button → redirected to your website
4. User completes 'verification' on your website
5. Your website sends a POST request to the bot's `/verify` endpoint
6. Bot assigns the "Verified" role to the user
7. Bot logs the verification in `#verification-logs` (and you get the token)

## Getting User's Discord Info for Your Website

To send the correct data to the webhook, your website needs the user's Discord ID and the guild ID. Common approaches:

1. **Discord OAuth2**: Have users log in with Discord on your website
2. **URL Parameters**: Include the user ID and guild ID in the verification URL
3. **Verification Code**: Generate a unique code linked to the Discord user

## Example Website Integration

```javascript
// After user completes verification on your website
async function notifyDiscordBot(discordUserId, guildId) {
    const response = await fetch('http://your-bot-server:3000/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            discordUserId: discordUserId,
            discordUsername: 'optional',
            guildId: guildId
        })
    });
    
    const result = await response.json();
    return result.success;
}
```

## Environment Variables (Optional)

You can use environment variables instead of hardcoding:

```bash
export BOT_TOKEN="your-token"
export WEBHOOK_PORT=3000
```

Then modify `bot.js` to use `process.env.BOT_TOKEN` etc.
