#!/bin/bash
#
# Fix newlines in temp.txt
# Converts literal \n to actual line breaks and removes surrounding quotes
#

FILE="temp.txt"

if [ ! -f "$FILE" ]; then
    echo "❌ Error: $FILE not found"
    exit 1
fi

echo "🔧 Fixing newlines in $FILE..."

# Replace literal \n with actual newlines and remove quotes
sed 's/\\n/\n/g' "$FILE" | sed 's/^"//; s/"$//' > "${FILE}.tmp"

# Replace original file
mv "${FILE}.tmp" "$FILE"

echo "✅ Done! File now has proper line breaks"
echo ""
echo "First 10 lines:"
head -10 "$FILE"
