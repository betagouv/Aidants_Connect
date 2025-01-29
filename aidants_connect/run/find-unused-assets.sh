while IFS= read -r -d '' file; do
  TARGET="$file"
  if [[ "$file" == *scss ]]; then
    TARGET=$(echo "$file" | sed -E 's/\.scss/\.css/g')
  fi

  if ! grep "$TARGET" -rqI . --exclude-dir=".git" --exclude-dir="*__pycache__" --exclude-dir="*staticfiles" --exclude="**/*.map"; then
    echo "$file"
  fi
done < <(find . -wholename "*/static/*" -type f -print0 | xargs -0 basename -a -z)
