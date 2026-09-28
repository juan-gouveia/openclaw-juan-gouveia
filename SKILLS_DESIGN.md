# Skills we're building

## Random Picture of the Day

1. What does this skill do? One sentence.
  - This skill requests a picture from the user and stores it on a designated folder.

2. What input does the agent need? What do you give it, in what format — and what does it already know from the five configuration files?
  - Agent needs to randomly select a time of day (between 09:00 and 21:00, Spain time) each day
  - Send a message using Telegram requesting the "Picture of the day"
  - Receive the picture
  - Rename the picture to "picoftheday - XXX"
  - Store it inside a previously designated Google Drive folder

3. What does a good output look like? Format, destination (a Doc, a Calendar event, a Telegram message…), and how you'll know it worked.
  - There's a picture properly renamed and stored corresponding to the current day
  - Agent should be able to list back existing pictures inside the folder

4. Implementation (2026-09-28) — `skills/picoftheday/`
  - Name format: `picoftheday - NNN - DD-MM-YY.jpg` (NNN from 001, next = highest in folder + 1), Drive folder "Pic of the Day" via Zapier MCP
  - `picoftheday-planner` automation (08:50 Europe/Madrid) picks a random time and creates a one-shot job that sends the request on Telegram
  - Upload uses the Telegram file URL (Zapier only accepts public URLs); token copy in secret store entry `TELEGRAM_BOT_TOKEN_FILES`


