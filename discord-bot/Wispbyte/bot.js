const { Client, GatewayIntentBits, PermissionFlagsBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ChannelType } = require('discord.js');
const express = require('express');
const cors = require('cors');

// ============================================
// CONFIGURATION - Put your token directly here
// ============================================
const CONFIG = {
    BOT_TOKEN: 'yourbottokenhere',
    VERIFICATION_WEBSITE_URL: 'https://verifikat.codeberg.page/Verifikat/',
    VERIFICATION_CHANNEL_NAME: 'verify',
    LOG_CHANNEL_NAME: 'verification-logs',
    VERIFIED_ROLE_NAME: 'Verified',
    BOT_ROLE_NAME: 'VerifiKat',
    WEBHOOK_PORT: 3000
};

// ============================================
// DISCORD CLIENT SETUP
// ============================================
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

// ============================================
// EXPRESS SERVER FOR WEBHOOK
// ============================================
const app = express();
app.use(cors());
app.use(express.json());

// Webhook endpoint - your website calls this when verification is complete
app.post('/verify', async (req, res) => {
    const { discordUserId, discordUsername, guildId } = req.body;

    if (!discordUserId || !guildId) {
        return res.status(400).json({ error: 'Missing discordUserId or guildId' });
    }

    try {
        const guild = client.guilds.cache.get(guildId);
        if (!guild) {
            return res.status(404).json({ error: 'Guild not found' });
        }

        const member = await guild.members.fetch(discordUserId);
        if (!member) {
            return res.status(404).json({ error: 'Member not found' });
        }

        // Get the verified role
        const verifiedRole = guild.roles.cache.find(r => r.name === CONFIG.VERIFIED_ROLE_NAME);
        if (!verifiedRole) {
            return res.status(404).json({ error: 'Verified role not found' });
        }

        // Add the role to the user
        await member.roles.add(verifiedRole);

        // Log the verification
        const logChannel = guild.channels.cache.find(
            c => c.name === CONFIG.LOG_CHANNEL_NAME
        );

        if (logChannel) {
            const logEmbed = new EmbedBuilder()
                .setColor(0x00FF00)
                .setTitle('✅ User Verified')
                .setDescription(`**${discordUsername || member.user.tag}** has been verified!`)
                .addFields(
                    { name: 'User ID', value: discordUserId, inline: true },
                    { name: 'Username', value: member.user.tag, inline: true }
                )
                .setTimestamp();

            await logChannel.send({ embeds: [logEmbed] });
        }

        console.log(`✅ Verified user: ${member.user.tag}`);
        res.json({ success: true, message: `User ${member.user.tag} verified successfully` });

    } catch (error) {
        console.error('Verification error:', error);
        res.status(500).json({ error: 'Failed to verify user' });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'ok', bot: client.user?.tag || 'not ready' });
});

// Root endpoint
app.get('/', (req, res) => {
    res.json({ status: 'VerifiKat bot is running', bot: client.user?.tag || 'not ready' });
});

// ============================================
// BOT FUNCTIONS
// ============================================

async function ensureBotRole(guild) {
    let botRole = guild.roles.cache.find(r => r.name === CONFIG.BOT_ROLE_NAME);

    if (!botRole) {
        console.log(`Creating bot role "${CONFIG.BOT_ROLE_NAME}" in ${guild.name}...`);
        try {
            botRole = await guild.roles.create({
                name: CONFIG.BOT_ROLE_NAME,
                color: 0x5865F2,
                hoist: true,
                reason: 'Bot role for verification system'
            });
            console.log(`✅ Created bot role: ${botRole.name} (hoisted)`);

            // Assign the role to the bot
            const botMember = await guild.members.fetch(client.user.id);
            if (botMember) {
                await botMember.roles.add(botRole);
                console.log(`✅ Assigned bot role to self`);
            }
        } catch (error) {
            console.error('Failed to create bot role:', error.message);
        }
    } else {
        // If role exists but isn't hoisted, update it
        if (!botRole.hoist) {
            try {
                await botRole.edit({ hoist: true });
                console.log(`✅ Updated bot role to be hoisted`);
            } catch (error) {
                console.error('Failed to update bot role:', error.message);
            }
        }
    }

    return botRole;
}

async function ensureVerifiedRole(guild) {
    let verifiedRole = guild.roles.cache.find(r => r.name === CONFIG.VERIFIED_ROLE_NAME);

    if (!verifiedRole) {
        console.log(`Creating verified role "${CONFIG.VERIFIED_ROLE_NAME}" in ${guild.name}...`);
        try {
            verifiedRole = await guild.roles.create({
                name: CONFIG.VERIFIED_ROLE_NAME,
                color: 0x00FF00,
                reason: 'Role for verified users'
            });
            console.log(`✅ Created verified role: ${verifiedRole.name}`);
        } catch (error) {
            console.error('Failed to create verified role:', error.message);
        }
    }

    return verifiedRole;
}

async function ensureLogChannel(guild) {
    let logChannel = guild.channels.cache.find(
        c => c.name === CONFIG.LOG_CHANNEL_NAME && c.type === ChannelType.GuildText
    );

    if (!logChannel) {
        console.log(`Creating log channel "#${CONFIG.LOG_CHANNEL_NAME}" in ${guild.name}...`);
        try {
            logChannel = await guild.channels.create({
                name: CONFIG.LOG_CHANNEL_NAME,
                type: ChannelType.GuildText,
                permissionOverwrites: [
                    {
                        // Hide from everyone
                        id: guild.id,
                        deny: [PermissionFlagsBits.ViewChannel]
                    }
                ],
                reason: 'Channel for verification logs'
            });
            console.log(`✅ Created log channel: #${logChannel.name}`);
        } catch (error) {
            console.error('Failed to create log channel:', error.message);
        }
    }

    return logChannel;
}

async function ensureVerifyChannel(guild, verifiedRole) {
    let verifyChannel = guild.channels.cache.find(
        c => c.name === CONFIG.VERIFICATION_CHANNEL_NAME && c.type === ChannelType.GuildText
    );

    if (!verifyChannel) {
        console.log(`Creating verify channel "#${CONFIG.VERIFICATION_CHANNEL_NAME}" in ${guild.name}...`);
        try {
            verifyChannel = await guild.channels.create({
                name: CONFIG.VERIFICATION_CHANNEL_NAME,
                type: ChannelType.GuildText,
                permissionOverwrites: [
                    {
                        // Everyone can see but NOT send messages
                        id: guild.id,
                        allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.ReadMessageHistory],
                        deny: [PermissionFlagsBits.SendMessages]
                    },
                    {
                        // Verified users CANNOT see this channel
                        id: verifiedRole.id,
                        deny: [PermissionFlagsBits.ViewChannel]
                    },
                    {
                        // Bot can send messages
                        id: client.user.id,
                        allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.EmbedLinks]
                    }
                ],
                reason: 'Channel for user verification'
            });
            console.log(`✅ Created verify channel: #${verifyChannel.name}`);
        } catch (error) {
            console.error('Failed to create verify channel:', error.message);
        }
    }

    return verifyChannel;
}

async function lockDownOtherChannels(guild, verifiedRole, verifyChannel, logChannel) {
    console.log(`🔒 Setting up channel permissions for verification system...`);
    
    let lockedCount = 0;
    let skippedCount = 0;
    
    for (const channel of guild.channels.cache.values()) {
        // Skip the verify channel and log channel
        if (channel.id === verifyChannel?.id || channel.id === logChannel?.id) {
            continue;
        }
        
        // Only process text channels and categories
        if (channel.type !== ChannelType.GuildText && channel.type !== ChannelType.GuildCategory) {
            continue;
        }
        
        try {
            // Check current @everyone permissions
            const everyonePerms = channel.permissionOverwrites.cache.get(guild.id);
            
            // Check if @everyone is already explicitly denied ViewChannel
            const isAlreadyHidden = everyonePerms?.deny?.has(PermissionFlagsBits.ViewChannel);
            
            if (isAlreadyHidden) {
                // Channel is already hidden from @everyone, don't touch it
                skippedCount++;
                continue;
            }
            
            // Channel is visible to @everyone, so we need to:
            // 1. Allow Verified role to view it
            // 2. Deny @everyone from viewing it
            
            await channel.permissionOverwrites.edit(verifiedRole.id, {
                ViewChannel: true
            });
            
            await channel.permissionOverwrites.edit(guild.id, {
                ViewChannel: false
            });
            
            lockedCount++;
        } catch (error) {
            // Silently skip channels we can't modify
        }
    }
    
    console.log(`✅ Locked ${lockedCount} channels (only Verified users can see them)`);
    if (skippedCount > 0) {
        console.log(`ℹ️ Skipped ${skippedCount} channels (already hidden from @everyone)`);
    }
}

async function sendVerificationMessage(guild, verifyChannel) {
    if (!verifyChannel) {
        console.log(`⚠️ No verify channel available`);
        return;
    }

    // Check if we already sent a verification message
    try {
        const messages = await verifyChannel.messages.fetch({ limit: 50 });
        const existingMessage = messages.find(
            m => m.author.id === client.user.id && m.embeds.length > 0
        );

        if (existingMessage) {
            console.log(`Verification message already exists in #${CONFIG.VERIFICATION_CHANNEL_NAME}`);
            return;
        }
    } catch (error) {
        console.error('Failed to fetch messages:', error.message);
    }

    const embed = new EmbedBuilder()
        .setColor(0x5865F2)
        .setTitle('🔐 Verification Required')
        .setDescription(
            'Welcome! To access the server, you need to verify your account.\n\n' +
            'Click the button below to start the verification process.'
        )
        .addFields(
            { name: '📋 Instructions', value: '1. Click the "Verify" button\n2. Complete the verification on our website\n3. You will automatically receive the Verified role' }
        )
        .setFooter({ text: 'If you have issues, contact a moderator' });

    const button = new ActionRowBuilder()
        .addComponents(
            new ButtonBuilder()
                .setLabel('Verify')
                .setStyle(ButtonStyle.Link)
                .setURL(CONFIG.VERIFICATION_WEBSITE_URL)
                .setEmoji('✅')
        );

    try {
        await verifyChannel.send({ embeds: [embed], components: [button] });
        console.log(`✅ Sent verification message to #${CONFIG.VERIFICATION_CHANNEL_NAME}`);
    } catch (error) {
        console.error('Failed to send verification message:', error.message);
    }
}

async function setupGuild(guild) {
    console.log(`\n🔧 Setting up guild: ${guild.name}`);

    // Create roles first
    await ensureBotRole(guild);
    const verifiedRole = await ensureVerifiedRole(guild);
    
    // Create channels
    const logChannel = await ensureLogChannel(guild);
    const verifyChannel = await ensureVerifyChannel(guild, verifiedRole);
    
    // Lock down other channels so only verified users can see them
    await lockDownOtherChannels(guild, verifiedRole, verifyChannel, logChannel);
    
    // Send the verification message
    await sendVerificationMessage(guild, verifyChannel);

    console.log(`✅ Guild setup complete: ${guild.name}\n`);
}

// ============================================
// BOT EVENTS
// ============================================

client.once('ready', async () => {
    console.log('========================================');
    console.log(`🤖 Bot logged in as ${client.user.tag}`);
    console.log('========================================\n');

    // Setup all guilds the bot is in
    for (const guild of client.guilds.cache.values()) {
        await setupGuild(guild);
    }

    // Start the webhook server
    app.listen(CONFIG.WEBHOOK_PORT, () => {
        console.log(`🌐 Webhook server running on port ${CONFIG.WEBHOOK_PORT}`);
        console.log(`   POST /verify - Endpoint for your verification website`);
        console.log(`   GET /health  - Health check endpoint\n`);
    });
});

// When bot joins a new guild
client.on('guildCreate', async (guild) => {
    console.log(`📥 Joined new guild: ${guild.name}`);
    await setupGuild(guild);
});

// ============================================
// START THE BOT
// ============================================

client.login(CONFIG.BOT_TOKEN);
