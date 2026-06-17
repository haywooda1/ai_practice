wallet = 41
print (wallet)

wallet = 32
print (wallet)

day = 8
print (day)


print (3 + 6)
print (day + 3)

# Boolean variables
light_is_on = False

if light_is_on:
    print ("The light is on!")
else:    print ("The light is off!")


import random
print (random.randint(1, 10))
# or you can create a random float integeter (which has the decimals)
print (random.random())

answer = random.randint(1, 3)
if answer == 1:
    print ("Yes")
elif answer == 2:
    print ("No")
else:
    print ("Maybe")

class_grades = {"Math": 95, "Science": 78, "English": 92}
class_pass = {"Math": True, "Science": False, "English": True}
print (class_grades)
print (class_pass)
#pass_values = class_pass.values()
pass_list = list(class_pass.values())
print (pass_list)
remainder = 10 % 2
print (f"This is the remainder: {remainder}")

import os
help (os)