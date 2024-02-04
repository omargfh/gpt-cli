# GPT CLI

## Usage
```bash
$ > python3 gpt.py -i chatFile -c
You: How to find files on mac?
Assistant: You can use the `find` command in the Terminal to search for files on your Mac. Here is an example:

find /path/to/search -name "filename"


Replace `/path/to/search` with the directory where you want to start the search, and `"filename"` with the name of the file you are looking for. 

For example, to find all files named `example.txt` in your Documents folder, you can use the following command:

find ~/Documents -name "example.txt"

This will list all files matching the specified name in the given directory or any subdirectories.
You: Thank you
Assistant: You're welcome! If you have any more questions, feel free to ask.
You: q
```

## Requirements
```bash
export OPENAI_API_KEY=KEY && python3.gpt.oy
```
