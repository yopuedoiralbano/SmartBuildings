from collections import namedtuple
from ortools.sat.python import cp_model
import numpy as np

# Need an array of length T, with T number of time periods
# To keep it simple, we'll start by saying that at any point in time a
# machine is either on or off (1 is on, 0 is off)
# 
# We have n all_machines (let n = 5 for simplicity)
# Each machine has a (static for simplicity) power consumption

T = 10 # start with 10 time periods
all_times = range(T)
n = 5 # start with 5 machines
all_machines = range(n)
machine_power = [100, 200, 150, 50, 25]
required_periods = [[(2,4),(5,7)], [], [(4,8)], [(1,4), (9,10)], [(2,9)]]
total_time_on = [4,1,4,4,7]

def convert_required_to_schedule(required_periods, T,n):
    required_schedule = np.zeros((n,T), dtype=int)
    for machine_id, machine_periods in enumerate(required_periods):
        for period in machine_periods:
            for t in range(period[0],period[1]):
                required_schedule[machine_id, t] = 1
    return required_schedule

model = cp_model.CpModel()

# Build an array of whether the all_machines are on or off - machine_power[machine_id, time]

final_schedule = {}
for t in all_times:
    for m in all_machines:
        final_schedule[(m,t)] = model.NewBoolVar('power_m{}t{}'.format(m,t))

required_schedule = convert_required_to_schedule(required_periods,T,n)


# Constraints

# Each machine must be on for its total time on
# model.Add(Sum of machine power is equal to total time on) - this constraint is verified working
for m_id in all_machines:
    model.Add(sum(final_schedule[(m_id,t)] for t in all_times) == total_time_on[m_id])

# Each machine MUST be on during its requested times - this constraint is working. BUT it will cause infeasible solutions if total_time_on[m] < total requested times
model.Add(sum(final_schedule[(m_id,t)]*required_schedule[m_id,t] for m_id in all_machines for t in all_times) == required_schedule.sum())

# Objective - this does not seem to be working
# What do I want to get out of the objective?
# I want to minimize the largest amount of energy spent

# Idea to start - maximize the value at a certain point - verified working
# model.Maximize(final_schedule[(0,5)])

# Idea 2 - maximize the energy used, only specify the total number of periods that a machine should be powered on - verified working
# periods_on = 8
# model.Add(sum(final_schedule[(m_id,t)] for t in all_times for m_id in all_machines) == periods_on)
# model.Minimize(sum(final_schedule[(m_id,t)]*machine_power[m_id] for t in all_times for m_id in all_machines))

# FOUND IT - if I change the line above to 'max' rather than 'sum', it should still work. Because you would still 
#   get the minimum power value, which should be the 25. But it gives 200! So it looks like this framework can't minimize a max
#   Let's try that simple example with AddMaxEquality

# power_schedule = {}
# for t in all_times:
#     for m in all_machines:
#         power_schedule[(m,t)] = model.NewIntVar(0, 1000, 'actual_power_m{}t{}'.format(m,t))
#         model.Add(power_schedule[(m,t)] == final_schedule[(m,t)]*machine_power[m])

# periods_on = 8
# model.Add(sum(final_schedule[(m_id,t)] for t in all_times for m_id in all_machines) == periods_on)
# obj_var = model.NewIntVar(0, 1000, 'largest_power')
# model.AddMaxEquality(obj_var, [power_schedule[(m_id,t)] for t in all_times for m_id in all_machines])
# model.Minimize(obj_var)

# So it turns out AddMaxEquality CAN'T TAKE AN EXPRESSION (see https://github.com/google/or-tools/issues/1192)
# However, you can evaluate the expression beforehand, then put that into max equality!

#Now let's try it with our full set of constraints
maximum_possible_power = sum(machine_power)

power_schedule = {}
for t in all_times:
    for m in all_machines:
        power_schedule[(m,t)] = model.NewIntVar(0, 1000, 'actual_power_m{}t{}'.format(m,t))
        model.Add(power_schedule[(m,t)] == final_schedule[(m,t)]*machine_power[m])

total_per_time_period = []
for t in all_times:
    total_per_time_period.append(model.NewIntVar(0,1000, 'total_for_period{}'.format(t)))
    model.Add(sum(power_schedule[(m_id, t)] for m_id in all_machines) == total_per_time_period[t])
    

obj_var = model.NewIntVar(0,maximum_possible_power, 'peak_power')
model.AddMaxEquality(obj_var, total_per_time_period)
model.Minimize(obj_var)

solver = cp_model.CpSolver()
status = solver.Solve(model)
print('Status: %s' % solver.StatusName(status))
print(model.Validate()) #Only prints if status is MODEL_INVALID
print('Objective Value: {}'.format(solver.ObjectiveValue()))

# Prints the total power used in each time period
print(([sum(solver.Value(final_schedule[(m_id,t)])*machine_power[m_id] for m_id in all_machines) for t in all_times]))
# Prints the final schedule. This can be updated by using a solver callback
for m_id in all_machines:
    retStr = '['
    for time in all_times:
        retStr += str(solver.Value(final_schedule[(m_id,time)]))
    retStr = retStr + ']'
    print(retStr)

# A couple notes - this still doesn't find a perfect solution - it only minimizes the largest value. Therefore it doesn't fully flatten load - need some more constraints to make that happen
# You can't currently have multiple objective functions - you could do a weighting of their sum, where you put a larger coefficient on the thing that matters more
# Another solution here https://github.com/google/or-tools/issues/1344

