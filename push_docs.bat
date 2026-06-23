@echo off
cd /d C:\fralib
git checkout master 2>&1
git merge --ff-only 39ad94c 2>&1
git push github master 2>&1
git push origin master 2>&1