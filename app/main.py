import bottle
import json
import heapq
import random
import copy

################################################################################
# Taunts                                                                    #
################################################################################

tList = ['Feel the power of the mongoose!','I like to move it move it!','Listen to my mix tape!','You wanna go bruh? Wanna go? HUH?','Staying alive! Staying alive!','Pretty good eh?','Do you fear death?','Let of some ssssssteam...','PURGEEEEEEEE','Come on, kill meeee!','You require more Vespene Gas!','You require more pylons!','Require more overlords!!!','Fear the power of the force...','My goose is bigger than yours!']
lenTList = len(tList)-1
################################################################################
# Constants                                                                    #
################################################################################
snakeName = 'snakes-on-a-plane'
directions = {
	(-1, 0): 'left',
	(1, 0): 'right',
	(0, -1): 'up',
	(0, 1): 'down'
}

trapSamples = 20
idlePathSamples = 20

################################################################################
# Classes                                                                      #
################################################################################

##
# Basic priority queue, minimum value at top
#
class PriorityQueue:
	def __init__(self):
		self.elements = []
	
	def empty(self):
		return len(self.elements) == 0
	
	def enqueue(self, element, priority):
		heapq.heappush(self.elements, (priority, element))
	
	def dequeue(self):
		return heapq.heappop(self.elements)[1]

##
# Used for converting backwards path returned by A* to forwards, also finding
# direction to move
#

def pathCameFrom(cameFrom, goal):
	goTo = { goal: None }
	start = goal
	while cameFrom[start]:
		goTo[cameFrom[start]] = start
		start = cameFrom[start]
	return Path(goTo, start)

class Path:
	def __init__(self, goTo, start):
		self.goTo = goTo
		self.start = start

	def direction(self):
		nxt = self.goTo[self.start]
		return (nxt[0] - self.start[0], nxt[1] - self.start[1])

##
# Grid to use for pathfinding, has obstructions to be navigated around
#
class Grid:
	def __init__(self, width, height):
		self.width = width
		self.height = height
		self.cells = [ [ 0 for y in range(height) ] for x in range(width) ]
	
	# Finds a random, unobstructed cell on the grid
	def random(self):
		cell = None
		while cell == None or self.obstructed(cell):
			x = random.randint(0, self.width - 1)
			y = random.randint(0, self.height - 1)
			cell = (x, y)
		return cell

	# Checks if the grid contains a cell
	def contains(self, cell):
		return (cell[0] >= 0
			and cell[1] >= 0
			and cell[0] < self.width
			and cell[1] < self.height)

	# Obstructs a cell on the grid
	def obstruct(self, cell):
		if self.contains(cell):
			self.cells[cell[0]][cell[1]] = 1
		
	# Checks if a cell on the grid is obstructed
	def obstructed(self, cell):
		return self.cells[cell[0]][cell[1]] == 1

	# Heuristic for pathfinding, not currently used for anything
	# most likely use it to represent risk
	def heuristic(self, cell):
		return self.cells[cell[0]][cell[1]]

	# Finds neighbours to a cell on the grid
	def neighbours(self, cell):
		neighbours = []
		for direction in directions:
			neighbour = (cell[0] + direction[0], cell[1] + direction[1])
			
			# Check if on grid, and not obstructed
			if self.contains(neighbour) and not self.obstructed(neighbour):
				neighbours.append(neighbour)
		
		return neighbours

################################################################################
# Functions                                                                    #
################################################################################

# xDist + yDist
def manDist(a, b):
	return abs(a[0] - b[0]) + abs(a[1] - b[1])

# A* search, uses grid's heuristic
def aStar(grid, start, goal):
	frontier = PriorityQueue()
	frontier.enqueue(start, 0)
	cameFrom = { start: None }
	costSoFar = { start: 0 }

	while not frontier.empty():
		current = frontier.dequeue()
		if current == goal:
			return pathCameFrom(cameFrom, goal)

		for neighbour in grid.neighbours(current):
			cost = costSoFar[current] + grid.heuristic(neighbour)

			if neighbour not in costSoFar or cost < costSoFar[neighbour]:
				costSoFar[neighbour] = cost
				priority = cost + manDist(neighbour, goal)
				frontier.enqueue(neighbour, priority)
				cameFrom[neighbour] = current
	return False

"""
def ratePosition(grid, start, samples):
		passes = 0
		for i in range(samples):
			goal = grid.random()
			if aStar(grid, start, goal):
				passes += 1
		return float(passes) / samples

def isTrap(grid, start):
	score = ratePosition(grid, start, trapSamples)
	return score < trapEscapePercentageNeeded

def isPathTrap(grid, path):		#determine if we take a path or not
	grid = copy.deepcopy(grid)	#makes grid copy
	curr = path.start			#create iterator
	grid.obstruct(curr)			#go through grid and obstruct it
	while path.goTo[curr]:		#
		grid.obstruct(curr)
		curr = path.goTo[curr]
	return isTrap(grid, curr)
"""

def isPositionBetter(grid, snake, current, pathTo, to):
	# Passes
	currentPasses = 0
	toPasses = 0
	
	# New grid
	toGrid = copy.deepcopy(grid)
	
	# Loop over path and count
	curr = current
	count = 0
	while pathTo.goTo[curr]:		#
		curr = pathTo.goTo[curr]
		count += 1

	x = len(snake['coords']) - count
	while x > 0:
		toGrid.obstruct(snake['coords'][x - 1])
		x -= 1

	if len(snake['coords']) >= count:
		curr = current
		curr = pathTo.goTo[curr]
		while curr:
			toGrid.obstruct(curr)
			curr = pathTo.goTo[curr]
	else:
		curr = current
		curr = pathTo.goTo[curr]
		index = 0
		while curr:
			if index >= count - len(snake['coords']):
				toGrid.obstruct(curr)
			curr = pathTo.goTo[curr]
			index += 1
		
	for _ in range(trapSamples):
		goal = grid.random()
		if aStar(grid, current, goal):
			currentPasses += 1
		if aStar(toGrid, to, goal):
			toPasses += 1
	return toPasses < currentPasses


################################################################################
# Server                                                                       #
################################################################################

@bottle.get('/')
def index():
	return """<a href="https://github.com/sendwithus/battlesnake-python">battlesnake-python</a>"""
#-------------------------------------------------------------------------------
@bottle.post('/start')
def start():
	data = bottle.request.json
	# Request:
	#	game_id, width, height
	
	return json.dumps({
		'name': snakeName,
		'color': '#8B3626',
		'head_url': 'http://i.imgur.com/7hhZkaN.gif',
		'taunt': 'GRAWWRRGGGGGGGGGG!'
	})
#-------------------------------------------------------------------------------
@bottle.post('/move')
def move():
	data = bottle.request.json
	# Request:
	#	game_id, turn, board, snakes, food
	
	ourSnake = None
 	
 	# Find our snake
 	for snake in data['snakes']:
 		if snake['name'] == snakeName:
 			ourSnake = snake
 			break
 	
	grid = Grid(len(data['board'][0]), len(data['board']))				#makes base grid
	for snake in data['snakes']:										#sorts through snakes
		for coord in snake['coords']:									#get all snake coords
			grid.obstruct(tuple(coord))									#make obstructions
		if snake['name'] != snakeName:									#if snake is not our snake
			for direction in directions:								#make all snake heads a obstruction
				if len(snake['coords']) >= len(ourSnake['coords']): 	# if other snake larger, then obstruct where it can move to
					head = snake['coords'][0]							#
					movement = (head[0] + direction[0], head[1] + direction[1])	#
					grid.obstruct(movement)								#
	
	#-------GET FOODS
	possibleFoods = []
	for food in data['food']:
		dist = manDist(tuple(ourSnake['coords'][0]), tuple(food))
		skip = False
		for snake in data['snakes']:
			if snake['name'] != snakeName and manDist(tuple(snake['coords'][0]), tuple(food)) <= dist:
				skip = True
				break
		if not skip:
			possibleFoods.append(tuple(food))
			
	#-------GET CLOSEST FOOD
	closestFoodDist = 0
	closestFood = None
	for food in possibleFoods:
		d = manDist(tuple(ourSnake['coords'][0]), food)
		if d < closestFoodDist or closestFood == None:
			closestFood = food
			closestFoodDist = d
	idle = False
	
	if closestFood != None:
		path = aStar(grid, tuple(ourSnake['coords'][0]), closestFood)
		if path != False and not isPositionBetter(grid, ourSnake, tuple(ourSnake['coords'][0]), path, closestFood):
			move = directions[path.direction()]
		else:
			idle = True
	else:
		idle = True
	
	
	#------IDLE MOVEMENTS
	simpleMovements = False
	if idle:
		path = False
		ind = 0
		while not path and ind < idlePathSamples:
			goal = grid.random()
			tmpPath = aStar(grid, tuple(ourSnake['coords'][0]), goal)
			if tmpPath != False and not isPositionBetter(grid, ourSnake, tuple(ourSnake['coords'][0]), tmpPath, goal):
				path = tmpPath
			ind+= 1
		if path:
			move = directions[path.direction()]
		else:
			simpleMovements = True
			
	if simpleMovements:
		bGrid = Grid(len(data['board'][0]), len(data['board']))				#makes base grid
		for snake in data['snakes']:										#sorts through snakes
			for coord in snake['coords']:									#get all snake coords
				bGrid.obstruct(tuple(coord))									#make obstructions
		ourTail = tuple(ourSnake['coords'][-1])
		bGrid.cells[ourTail[0]][ourTail[1]] = 0
		
		path = False
		ind = 0
		while not path and ind < idlePathSamples:
			goal = bGrid.random()
			tmpPath = aStar(bGrid, tuple(ourSnake['coords'][0]), goal)
			if tmpPath != False:
				path = tmpPath
		if path:
			move = directions[path.direction()]
	
	
	
	#------DIRECTION CHECK ***FAILSAFE***
	if move == None:
		move = 'left'
		
	curdir = None
	for direction in directions:
		if move == directions[direction]:
			curdir = direction
			break
	
	curpos = tuple(ourSnake['coords'][0])
	transpos=  (curpos[0] + curdir[0], curpos[1] + curdir[1])
	
	if not grid.contains(transpos) or grid.obstructed(transpos):
		
		cGrid = Grid(len(data['board'][0]), len(data['board']))				#makes base grid
		for snake in data['snakes']:										#sorts through snakes
			for coord in snake['coords']:									#get all snake coords
				cGrid.obstruct(tuple(coord))									#make obstructions
		ourTail = tuple(ourSnake['coords'][-1])
		cGrid.cells[ourTail[0]][ourTail[1]] = 0
			
		for direction in directions:
			if direction == curdir:
				continue
			newpos = (curpos[0] + direction[0], curpos[1] + direction[1])
	
			if cGrid.contains(newpos) and not cGrid.obstructed(newpos):
				move = directions[direction]
				break
	#TO ADD: make so that it can check end of snakes adjacent to find openings
	#		 
	
	#------------------RETURN TO SERVER-----------
	return json.dumps({
		'move': move,
		'taunt': tList[random.randint(0,lenTList)]
	})
	#---------------------------------------------
	
	
#-------------------------------------------------------------------------------
@bottle.post('/end')
def end():
	data = bottle.request.json
	# Request:
	#	game_id

	return json.dumps({})
#-------------------------------------------------------------------------------
# Expose WSGI app
application = bottle.default_app()