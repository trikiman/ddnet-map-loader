STEP 1 remember all here

Server location C:\Users\rust-\Desktop\DDNet-18.7-win64\DDNet-Server.exe

Server loction config "C:\Users\rust-\Desktop\DDNet-18.7-win64\data\myServerconfig.cfg"

Visual Studio compiler ...\ddnet_control\compile.bat" ("E:\Program files\Microsoft Visual Studio")

Map location C:\Users\rust-\AppData\Roaming\DDNet\maps

dis url: [REDACTED - set in environment variable]

dis token: [REDACTED - set in environment variable DISCORD_BOT_TOKEN]

   - Channel 1: general - For broadcasting messages
   - Channel 2: msg-history - For game chat history
   - Channel 3: session - For session tracking


Step 2 
# App for Discord and DDNet Game Integration

This project creates a C++ application that connects to both Discord and DDNet game server, providing map management and session tracking functionality across multiple channels.



## Key ideas

1. **Connect to DDNet Server**  
   - ec_bindaddr "127.0.0.1"  # Only allow connections from localhost
   - ec_port 8303             # Port for ECON to listen on
   - ec_password "test123"    # Password for authentication




3. **Discord Bot Features** ✅
   - Map upload handling: Bot simulates double click when a map is uploaded
   - Reaction system: Adds confirmation emoji when map processing is complete
   - Interactive reactions: Re-processes map when emoji is clicked again
   - Map listing command: !map shows last 20 maps in folder
     
  format rules: 
         

         1034563956234272767_hui (17) 19:24-22-11-2024
         1034563956234272767_hui (16) 14:12-22-11-2024
         1034563956234272767_hui (15) 13:54-22-11-2024
         123                          13:52-22-11-2024
         1034563956234272767_hui (14) 18:56-21-11-2024
         1034563956234272767_hui (5)  17:58-21-11-2024
         1034563956234272767_hui (13) 13:58-21-11-2024
         1034563956234272767_hui (12) 15:53-20-11-2024
         1034563956234272767_hui (11) 19:10-19-11-2024
         1034563956234272767_hui (9)  15:01-19-11-2024
         1034563956234272767_hui (10) 13:23-19-11-2024
         1034563956234272767_hui (8)  13:28-18-11-2024
         1 (1)                        12:57-18-11-2024
         1034563956234272767_hui (7)  16:10-13-11-2024
         1034563956234272767_hui (6)  10:52-13-11-2024
         1034563956234272767_hui (4)  09:13-13-11-2024
         1                            03:44-13-11-2024
         Ham5 map                     01:57-13-11-2024
         1 (2)                        15:18-11-11-2024
         1034563956234272767_hui (3)  14:57-11-11-2024

5. **Chat history format**:  
   🤖 Discord bot connected successfully.
   👋 '[D] Ʈ¥4ƙą_' has left the game
   💬 triki: и стартани
   🎮 '[D] Ʈ¥4ƙą_' entered and joined the game
   ℹ️  '[D] Ʈ¥4ƙą_' joined team 2
   if link with ling on image bot will prewiew this image on channel.

4. **Session Format**

   📊 Session: ty4
   ─────────────────────────────
   ⏱  Duration:    13.0m
   🕒  Start:       00:37:58
   💬  Messages:    10
   🎮  Teams:       0
   ─────────────────────────────
   🔧 RCON Commands: 83 total
      • tele: 76 times
      • tele 1 0: 2 times
      • change_map 1: 1 times
      • change_map Rain: 1 times
      • help: 1 times
      • /cmdlist: 1 times
      • up: 1 times
   ─────────────────────────────
   🗺 Regular Commands: 15 total
      • kill: 5 times
      • spec: 3 times
      • team: 3 times
      • emote: 2 times
      • whisper: 2 times
   ─────────────────────────────
   🗺  Maps: total 3h
      Rain (1h34m) kefir (1h26m)

   All RCON Commands (352 total):

   access_level, access_status, add_map_votes, add_sqlserver, add_vote, addweapon, antibot, auth_add, auth_add_p, auth_change, auth_change_p, auth_list, 
   auth_remove, ban, ban_range, ban_region, ban_region_range, bans, bans_save, bindaddr, broadcast, c, change_map, clear_votes, cmdlist, conn_timeout, 
   conn_timeout_protection, console_enable_colors, console_output_level, converse, credits, dbg_curl, dbg_lognetwork, debug, deep, dnd, down, 
   dump_antibot, dump_log, dump_sqlservers, echo, emote, endless_hook, events, exec, eyeemote, force_pause, force_unpause, force_vote, freeze, 
   freezehammer, grenade, help, hot_reload, http_allow_insecure, infinite_jump, info, invincible, invite, jetpack, join, kick, kill, kill_pl, laser, 
   lasttp, left, livefreeze, load, lock, logappend, logfile, loglevel, logout, map, mapbug, mapinfo, me, moderate, move, move_raw, mute, muteid, muteip, 
   mutes, name_ban, name_bans, name_unban, ninja, ninjajetpack, password, pause, pause_game, pausevoted, points, practice, practicecmdlist, r, random_map, 
   random_unfinished_map, rank, rankteam, record, reload, reload_announcement, reload_censorlist, remove_vote, removeweapon, rescue, rescuemode, reset, 
   restart, rifle, right, rules, rust_version, save, save_dry, say, saytime, saytimeall, set_team, set_team_all, set_team_ddr, setjumps, settings, 
   shotgun, show_ips, showall, showothers, shutdown, solo, spec, specteam, specvoted, status, stdout_output_level, stoprecord, super, 
   sv_announcement_filename, sv_announcement_interval, sv_announcement_random, sv_auto_demo_max, sv_auto_demo_record, sv_banned_versions, sv_chat_delay, 
   sv_chat_initial_delay, sv_chat_penalty, sv_chat_threshold, sv_client_suggestion, sv_client_suggestion_bot, sv_client_suggestion_old, sv_connlimit, 
   sv_connlimit_time, sv_ddrace_rules, sv_ddrace_tune_reset, sv_deepfly, sv_default_timer_type, sv_demo_chat, sv_destroy_bullets_on_death, 
   sv_destroy_lasers_on_death, sv_dnsbl, sv_dnsbl_ban, sv_dnsbl_ban_reason, sv_dnsbl_chat, sv_dnsbl_host, sv_dnsbl_key, sv_dnsbl_vote, sv_dragger_range, 
   sv_emoticon_ms_delay, sv_emotional_tees, sv_endless_drag, sv_endless_super_hook, sv_eye_emote_change_delay, sv_fast_download, sv_freeze_delay, 
   sv_gametype, sv_global_emoticon_ms_delay, sv_hide_score, sv_high_bandwidth, sv_hit, sv_hostname, sv_inactivekick, sv_inactivekick_time, 
   sv_info_change_delay, sv_input_fifo, sv_invite, sv_invite_frequency, sv_ipv4only, sv_join_vote_delay, sv_kill_delay, sv_kill_protection, sv_map, 
   sv_map_vote, sv_map_window, sv_mapupdaterate, sv_max_afk_time, sv_max_clients, sv_max_clients_per_ip, sv_max_team_size, sv_min_team_size, sv_motd, 
   sv_name, sv_nameless_score, sv_netlimit, sv_netlimit_alpha, sv_no_weak_hook, sv_old_laser, sv_old_teleport_hook, sv_old_teleport_weapons, 
   sv_pause_frequency, sv_pause_messages, sv_pauseable, sv_plasma_per_sec, sv_plasma_range, sv_player_demo_record, sv_port, sv_practice, sv_rcon_bantime, 
   sv_rcon_helper_password, sv_rcon_max_tries, sv_rcon_mod_password, sv_rcon_password, sv_rcon_vote, sv_region_name, sv_regional_rankings, sv_register, 
   sv_register_extra, sv_register_url, sv_rejoin_team_0, sv_reload_when_empty, sv_rescue, sv_rescue_delay, sv_reserved_slots, 
   sv_reserved_slots_auth_level, sv_reserved_slots_pass, sv_reset_file, sv_reset_pickups, sv_rules_line1, sv_rules_line10, sv_rules_line2, sv_rules_line3, 
   sv_rules_line4, sv_rules_line5, sv_rules_line6, sv_rules_line7, sv_rules_line8, sv_rules_line9, sv_save_worse_scores, sv_savegames, 
   sv_saveswapgames_delay, sv_saveswapgames_penalty, sv_send_votes_per_tick, sv_server_info_per_second, sv_server_type, sv_shotgun_bullet_sound, 
   sv_show_all_default, sv_show_others, sv_show_others_default, sv_shutdown_when_empty, sv_sixup, sv_skill_level, sv_slash_me, sv_solo_server, 
   sv_spam_mute_duration, sv_spamprotection, sv_spectator_slots, sv_sql_queries_delay, sv_sql_servername, sv_sqlite_file, sv_strict_spectate_mode, 
   sv_swap, sv_swap_timeout, sv_team, sv_team0mode, sv_team_change_delay, sv_tee_historian, sv_tele_others_auth_level, sv_teleport_hold_hook, 
   sv_teleport_lose_weapons, sv_test_cmds, sv_time_in_broadcast_interval, sv_tournament_mode, sv_tune_reset, sv_use_sql, sv_van_conn_per_second, 
   sv_vanilla_antispoof, sv_vote_delay, sv_vote_kick, sv_vote_kick_bantime, sv_vote_kick_delay, sv_vote_kick_min, sv_vote_majority, sv_vote_map_delay, 
   sv_vote_max_total, sv_vote_pause, sv_vote_pause_time, sv_vote_spectate, sv_vote_spectate_rejoindelay, sv_vote_time, sv_vote_veto_time, 
   sv_vote_yes_percentage, sv_warmup, sv_welcome, swap, switch_open, tc, team, team0mode, teamrank, teamtop5, tele, telecursor, teleport, time, timecp, 
   timeout, timer, times, toggle, toggle_tune, top, top5, top5points, top5team, totele, totelecp, tp, tpxy, tune, tune_reset, tune_zone, tune_zone_dump, 
   tune_zone_enter, tune_zone_leave, tune_zone_reset, tunes, unban, unban_all, unban_range, undeep, unendless_hook, unfreeze, unfreezehammer, ungrenade, 
   uninfinite_jump, uninvite, unjetpack, unlaser, unlivefreeze, unlock, unmute, unmuteid, unninja, unrifle, unshotgun, unsolo, unsuper, unweapons, up, 
   vote, vote_mute, vote_mutes, vote_no, vote_unmute, votes, w, weapons, whisper, whispers

   ALL Regular Commands (98 total):

   addweapon, c, cmdlist, converse, credits, deep, dnd, emote, endless, eyeemote, grenade, help, infjump, info, invincible, invite, jetpack, join, kill, 
   laser, lasttp, list, livefreeze, load, lock, map, mapinfo, me, ninja, ninjajetpack, pause, pausevoted, points, practice, practicecmdlist, r, rank, 
   rankteam, removeweapon, rescue, rescuemode, rifle, rules, save, saytime, saytimeall, setjumps, settings, shotgun, showall, showothers, solo, spec, 
   specteam, specvoted, swap, tc, team, team0mode, teamrank, teamtop5, telecursor, teleport, time, timecp, timeout, timer, times, top, top5, top5points, 
   top5team, totele, totelecp, tp, tpxy, undeep, unendless, ungrenade, uninfjump, unjetpack, unlaser, unlivefreeze, unlock, unninja, unrifle, unshotgun, 
   unsolo, unweapons, w, weapons, whisper, whispers.

6. **Run any .map file on pc** (done)
   When you double-click any .map file on pc, it will hot_reload that map in game even if the application is not running.

   Detailed Logic:
   1. File Association: 
      - .reg file tells Windows to run program when .map file (X) is double-clicked
      - Example: Double-click Linear.map (this becomes X)

   2. Map Management:
      - LINEAR1: Original map stays where you double-clicked it
      - LINEAR2: Copy X to DDNet maps directory
      - LINEAR3: Copy that becomes current map (named as W)
      - W_backup: Original current map backed up

   Example Flow:
   - Double-click Linear.map while Kobra.map is running
   - End result:
   * LINEAR1: Original Linear.map (where you clicked)
   * LINEAR2: Linear.map (in DDNet maps folder)
   * LINEAR3: Kobra.map (contains Linear map content)
   * Original: Kobra_backup.map (original Kobra content)

   3. Server Communication:
      - Connect to DDNet's ECON interface
      - Send sv_map to get current map name (W)
      - Create backup of W as W_backup.map
      - Replace W with LINEAR3 (content of X)
      - Send hot_reload command
      - Verify map changed successfully
      - Keep window open to show results

   Result: You can hot_reload any map by double-clicking it, while keeping the original safe and preserving all copies.

   logic about backup in this file backuplogic.md

7. **Web interface**
   dragand drop .map file on web interface its simulate double click
   progress bar when map is loading    

   show last20 maps in C:\Users\rust9\AppData\Roaming\DDNet\maps folder in web interface
   port on web is 8299



8. **Authentication and Parsing Implementation**

   U can find worked version in folder "worked code only read folder"

9. **Response Timing**
   - Server may not respond immediately
   - Multiple attempts with delays improve reliability
   - Total timeout should be reasonable (e.g., 1-2 seconds)

10. **Response Format**
      - Responses include timestamp and log level
      - Map name is always after "Value:" prefix
      - May contain newlines and extra whitespace

11. **Error Handling**
      - Empty responses should be retried
      - Clean map name by removing non-printable characters
      - Verify map name is not empty after cleaning

12. **Verification**
      - After map change, verify new map is loaded
      - Use same parsing logic to confirm change
      - Multiple verification attempts may be needed

## Core Technologies
- **ECON Protocol**: External console for server control
- **TCP Sockets**: For reliable server communication
- **Discord API**: For bot integration
- **Windows API**: For file system operations

## Compilation
```batch
"C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat" && cl /EHsc /std:c++20 ddnet_control.cpp
```


## Next Steps
1. Implement Discord bot with map upload handling
2. Add !map command for history display
3. Create web interface for map control
4. Add file system watcher for .map files
5. Implement session tracking and statistics

## References
- DDNet Source: https://github.com/ddnet
- Game Server: 127.0.0.1:8303
- Maps Directory: C:/Users/rust-/AppData/Roaming/DDNet/maps
