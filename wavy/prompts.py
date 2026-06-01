from wavy.commands.commands_keys import *


def build_command_prompt(command_pool: dict[str, callable]) -> str:
    commands = ", ".join(f"'{k}'" for k in command_pool)

    return (
        "You are an assistant parsing commands in Russian from the input text. "
        "The input text may contain mistakes or imprecisions. "
        f"Your task is to map the user's intent to exactly one of the supported commands: {commands}. "
        "If the text does not match any of the commands or the intent is completely unclear, "
        "output the '#' in 'command_name'. "
        "You must strictly and exclusively output the required JSON structure."
    )


KWARGS_PROMPT = (
    "You are an assistant that extracts structured kwargs for a command from a user's voice input. "
    "The command name is already known; your job is to fill ONLY the kwargs required by the JSON schema. "
    "Return strictly valid JSON that matches the provided schema; do not add extra keys. "
    "Names(commands and arguments) should not contain extra characters unless the user has specified them. "
    "Use only single quotation marks(that is '') to indicate that a value is missing. "
    "Don't wrap them in other symbols. "
    "Totally do not use any other quotation marks(ex. "
    " or ``) to indicate that a value is missing. "
    "Follow the per-command extraction rules provided in the user message."
)


COMMAND_KWARGS_PROMPT_DICT = {
    CMD_LAUNCH_APP: (
        "Extract kwargs for launching an application from the user's voice input.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for app_name:\n"
        "- Lowercase only.\n"
        "- No spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian.\n"
        "Derive separator from how the user says the alias.\n"
        "- If the alias is multi-word, join with '_' (do not use spaces or hyphens)."
    ),
    CMD_CLOSE_APP: (
        "Extract kwargs for closing an application from the user's voice input.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for app_name:\n"
        "- Lowercase only.\n"
        "- No spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian.\n"
        "Derive separator from how the user says the alias.\n"
        "- If the alias is multi-word, join with '_' (do not use spaces or hyphens)."
    ),
    CMD_UNINSTALL_APP: (
        "Extract kwargs for uninstalling an application from the user's voice input.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for app_name:\n"
        "- Lowercase only.\n"
        "- No spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian.\n"
        "Derive separator from how the user says the alias.\n"
        "- If the alias is multi-word, join with '_' (do not use spaces or hyphens)."
    ),
    CMD_CREATE_FILE: (
        "Extract kwargs for creating a file.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for filename:\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian.\n"
        "- Must include a correct extension.\n"
        "  - If the user provided an extension, include it exactly once and lowercase.\n"
        "  - If the user did NOT provide an extension, infer it from context:\n"
        "    - script/code -> '.py'\n"
        "    - config/data -> '.json'\n"
        "    - plain text/notes/unknown -> '.txt'\n\n"
        "Rules for folder field (if present):\n"
        "- If the user did NOT specify any folder, leave folder field as an empty string(only '' without "
        ". '' is correct, "
        ""
        " is very bad).\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian.\n\n"
        "Rules for content:\n"
        "- No constraints; keep the intended text as-is."
    ),
    CMD_CREATE_FOLDER: (
        "Extract kwargs for creating a folder.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for name field (folder name):\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian."
    ),
    CMD_DELETE: (
        "Extract kwargs for deleting a file or folder.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for name field (file or folder name):\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian.\n"
        "- If it is a file, include the extension (infer it if needed using the same extension rules as create-file).\n\n"
        "Rules for folder field (if present):\n"
        "- If the user did NOT specify any folder, leave folder field as an empty string(only '' without "
        ". '' is correct, "
        ""
        " is very bad).\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian."
    ),
    CMD_RENAME: (
        "Extract kwargs for renaming a file or folder.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for old_name and new_name:\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian.\n"
        "- If the target is a file, both old and new names must include an extension.\n"
        "  - Preserve the old extension unless the user explicitly requests changing it.\n"
        "  - Ensure the new file name has exactly one extension, lowercase.\n\n"
        "Rules for folder field (if present):\n"
        "- If the user did NOT specify any folder, leave folder field as an empty string(only '' without "
        ". '' is correct, "
        ""
        " is very bad).\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Use Russian language for the name, do not mix English and Russian."
    ),
    CMD_RUN_SCRIPT: (
        "Extract kwargs for running a Python script.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for script_name:\n"
        "- Lowercase only.\n"
        "- Use ONLY '_' as a separator.\n"
        "- Do NOT include spaces.\n"
        "- Must include the '.py' extension exactly once."
    ),
    CMD_OPEN_SITE: (
        "Extract kwargs for opening a website.\n"
        "Return strictly JSON matching the schema.\n\n"
        "Rules for website_name:\n"
        "- Must be English only.\n"
        "- Must be exactly one token (no spaces).\n"
        "- Lowercase only.\n"
        "- Must include a top-level domain (TLD), e.g. 'google.com', 'wikipedia.org', 'github.com'.\n"
        "- If the user says a site without a TLD (e.g. 'google'), infer the most likely TLD (usually '.com').\n"
        "- Do NOT output protocol/path (no 'https://', no '/...'); output only the domain.\n\n"
        "Rules for query (if present):\n"
        "- No constraints; keep the intended text as-is."
    ),
}
