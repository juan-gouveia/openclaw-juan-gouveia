# Skills we're building

## Random Picture of the Day

1. What does this skill do? One sentence.
  - This skill requests a picture from the user and stores it on a designated folder.

2. What input does the agent need? What do you give it, in what format — and what does it already know from the five configuration files?
  - Agent needs to randomly select a time of day (between 09:00 and 21:00) each day
  - Send a message using Telegram requesting the "Picture of the day"
  - Receive the picture
  - Rename the picture to "picoftheday - <timestamp>"
  - Store it inside a previously designated folder

3. What does a good output look like? Format, destination (a Doc, a Calendar event, a Telegram message…), and how you'll know it worked.
  - There's a picture properly renamed and stored corresponding to the current day
  - Agent should be able to list back existing pictures inside the folder


## 