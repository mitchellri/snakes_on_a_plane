import bottle
import json
import heapq
import random

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
class Path:
	def cameFrom(cameFrom, goal):
		goTo = { goal: None }
		start = goal
		while cameFrom[start]:
			goTo[cameFrom[start]] = start
			start = cameFrom[start]
		return Path(goTo, start)

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
			return Path.cameFrom(cameFrom, goal)

		for neighbour in grid.neighbours(current):
			cost = costSoFar[current] + grid.heuristic(neighbour)

			if neighbour not in costSoFar or cost < costSoFar[neighbour]:
				costSoFar[neighbour] = cost
				priority = cost + manDist(neighbour, goal)
				frontier.enqueue(neighbour, priority)
				cameFrom[neighbour] = current
	return False


################################################################################
# Server                                                                       #
################################################################################

@bottle.get('/')
def index():
    return """
        <a href="https://github.com/sendwithus/battlesnake-python">
            battlesnake-python
        </a>
    """


@bottle.post('/start')
def start():
    data = bottle.request.json

    return json.dumps({
        'name': snakeName,
        'color': '#EF0006',
        'head_url': 'http://battlesnake-python.herokuapp.com',
        'taunt': 'battlesnake-python!'
    })


@bottle.post('/move')
def move():
    data = bottle.request.json

	ourSnake = None
    
    grid = Grid(len(data.board[0]), len(data.board))
    for snake in data.snakes:
        if snake.state == "alive":
            for coord in snake.coords:
                grid.obstruct(coord)
            if snake.name != snakeName:
                for direction in directions:
                    head = snake.coords[0]
                    movement = (head[0] + direction[0], head[1] + direction[1])
                    grid.obstruct(movement)
            else:
                ourSnake = snake
            
    path = aStar(grid, ourSnake.coords[0], data.food[0])
    
    
    move = 'left'
    
    if path != False:
        move = directions[path.direction()]
	

    return json.dumps({
        'move': move,
        'taunt': 'battlesnake-python!'
    })


@bottle.post('/end')
def end():
    data = bottle.request.json

    return json.dumps({})

# Expose WSGI app
application = bottle.default_app()