# [@sstmintgrtn_bot](https://t.me/sstmintgrtn_bot)

![@sstmintgrtn_bot](https://www.gravatar.com/avatar/7ceee8792cfff9591510a6fe04131afa?size=200&default=robohash&forcedefault=y)

The Telegram bot is designed to master the practical skills of integrating information systems and gain experience in working together on a project in a distributed team.

The bot combines various authoring functions written by students in the process of studying the discipline "system integration of software applications".
Each of the functions must implement interaction with an external information system.

**Test telegram bot** - [@sstmintgrtn_bot](https://t.me/sstmintgrtn_bot).

**Shared group with a bot** - [sstmintgrtn](https://t.me/sstmintgrtn). When pushed to any branch, test results will also appear in that group.

To run locally, add an `.env` file with your keys to the root of the project. Or add appropriate values to the environment variables of your operating system.

## Tokens

Links to information about tokens

[GITHUBTOKEN](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

[IPSTACK_API_KEY](https://ipstack.com/)

[OPENWEATHER_API_KEY](https://openweathermap.org). - To receive a token for the weather function, register and create a key on the OpenWeatherMap platform.

[COINMARKETCAP_API_KEY](https://coinmarketcap.com/api/documentation/v1/#section/Quick-Start-Guide).

[NASA_API_KEY](https://api.nasa.gov/).

```
LOGLEVEL=ERROR
TBOT_LOGLEVEL=ERROR
CONECTION_PGDB=
TBOTTOKEN=

EXAMPLETOKEN=1234567890
IPSTACK_API_KEY=
OPENWEATHER_API_KEY=
COINMARKETCAP_API_KEY=<your_coin_market_cap_api_key>
NASA_API_KEY=<your_nasa_api_key>
```

## Adding telegram bot functions.

Dear students, when implementing your functions, adhere to the following recommendations.
Your code should be placed in a separate file in the **src/functions/atomic** directory.
The code must be organized in a class that inherits from the abstract class **AtomicBotFunctionABC**

- commands: List[str] - list of commands to call your function
- authors: List[str] - your login on github.com
- about: str - short description
- description: str - a detailed description of the function with a description of the parameters if they are needed
- state: bool - state whether the function is enabled or disabled

## Please run tests and check code with pylint before submitting.

```
pylint .\src\functions\atomic\<your_file>.py
```

For an example, take a look at the file **[example_bot_function.py](https://github.com/IHVH/system-integration-bot-2/blob/master/src/functions/atomic/example_bot_function.py)**

Explore the capabilities of the library that is used in the project [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI).
