1. I made changes to line 3 of README.md on the main branch, and also made changes to the same line on your feature/stage-a branch.
2. When I ran `git merge feature/stage-a` on the main branch, Git detected a conflict in README.md because both branches modified the same line.
3. Git marked the conflict in README.md, and I had to manually resolve it by combining the changes from both branches. 