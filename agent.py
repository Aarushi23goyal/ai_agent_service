import os
import json
import subprocess
from openai import OpenAI


# ============================================================
# 1. OpenAI CLIENT
# ============================================================

client = OpenAI()


# ============================================================
# 2. TOOLS
# ============================================================

def git_status():
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "error": result.stderr
        }

    return {
        "status": result.stdout
    }


def git_diff():
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "error": result.stderr
        }

    return {
        "diff": result.stdout
    }


def read_file(filename):
    try:
        with open(filename, "r") as file:
            return {
                "content": file.read()
            }

    except Exception as e:
        return {
            "error": str(e)
        }


def create_file(filename, content):
    try:
        with open(filename, "w") as file:
            file.write(content)

        return {
            "status": "success",
            "message": f"{filename} created successfully"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# 3. GIVE TOOLS TO THE LLM
# ============================================================

tools = [

    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description":
                "Get the current status of the git repository. "
                "Use this to see which files have been modified, "
                "added, or deleted.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description":
                "Get the current uncommitted git diff. "
                "Use this to understand exactly what code changes "
                "have been made.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description":
                "Read the contents of a file in the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description":
                            "The path of the file to read."
                    }
                },
                "required": ["filename"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description":
                "Create a new file or overwrite an existing file "
                "with the supplied content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string"
                    }
                },
                "required": [
                    "filename",
                    "content"
                ]
            }
        }
    }
]


# ============================================================
# 4. TOOL EXECUTOR
# ============================================================

def execute_tool(function_name, arguments):

    if function_name == "git_status":
        return git_status()

    elif function_name == "git_diff":
        return git_diff()

    elif function_name == "read_file":
        return read_file(
            arguments["filename"]
        )

    elif function_name == "create_file":
        return create_file(
            arguments["filename"],
            arguments["content"]
        )

    else:
        return {
            "error": f"Unknown tool: {function_name}"
        }


# ============================================================
# 5. AGENT
# ============================================================

messages = [

    {
        "role": "system",
        "content": """
You are a Git Commit Assistant.

Your job is to inspect the user's current git changes
and prepare them for a commit.

You have access to tools that allow you to:

1. Check git status
2. Inspect git diff
3. Read files
4. Create files

Workflow:

- First inspect git status.
- Then inspect the git diff.
- Read relevant files if necessary to understand the changes.
- Analyze what the developer changed.
- Create a CHANGELOG.md describing the changes.
- Provide a concise conventional commit message.

Do NOT run git commit.
Do NOT run git push.
Do NOT delete files.
Do NOT modify source code.

Only create CHANGELOG.md.

When you finish, explain what you found and
provide the suggested commit message.
"""
    },

    {
        "role": "user",
        "content": """
Review my current changes and prepare them for a commit.

Create a CHANGELOG.md describing the changes
and suggest an appropriate conventional commit message.
"""
    }
]


# ============================================================
# 6. AGENT LOOP
# ============================================================

print("\n🤖 Git Commit Assistant started...\n")


while True:

    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages,
        tools=tools
    )

    message = response.choices[0].message

    # Add the assistant's response to conversation
    messages.append(message)

    # --------------------------------------------------------
    # If there are no tool calls, the agent is finished.
    # --------------------------------------------------------

    if not message.tool_calls:

        print("\n" + "=" * 60)
        print("🤖 FINAL RESPONSE")
        print("=" * 60)

        print(message.content)

        break

    # --------------------------------------------------------
    # Execute every tool requested by the LLM
    # --------------------------------------------------------

    for tool_call in message.tool_calls:

        function_name = tool_call.function.name

        arguments = json.loads(
            tool_call.function.arguments
        )

        print(
            f"🔧 Calling tool: {function_name}"
        )

        if arguments:
            print(
                f"   Arguments: {arguments}"
            )

        result = execute_tool(
            function_name,
            arguments
        )

        print(
            f"   Result: {result}\n"
        )

        # Send tool result back to the LLM
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            }
        )