###############
Cross Coverage
###############

ISAC supports extraction of data dependencies across different instructions in the log file. It can check for possible data hazards (RAW, WAW, WAR) between instructions. 
The hazards are checked for instructions belonging to the same window. The window size of the instruction is a parameter (by default taken as 32). 
The coverpoints are updated whenever the conditions mentioned in them are matched for a given instruction. 

Syntax for the coverpoints
===========================

Each coverpoint is a string constituting of three sections - opcode list, assign list and condition list separated by ``::`` symbol. In each of these lists symbol
``?`` signifies a don't care condition. The delimiter for elements of the list is ``:`` symbol. The template of a generic coverpoint is shown below:

``[list of opcodes]::[list of assignment statements]::[list of condition statements]``

Opcode List:
--------------
This is the list of instruction names against which we check the name of the current instruction in the queue. Here ``?`` signifies that we needn't check the name
for that instruction as that won't affect the conditions of that coverpoint. Opcode list is a list of tuples and don't care conditions.

An example of a opcode list : ``[(add,sub):?:?:(mul,mulh):?]``

Assign List:
-------------
This list contains the assigning statements for registers. These statements are evaluated using ``exec`` command. The register numbers are assigned to variables.
Under don't care conditions, no assignment is done.

An example of assign list: ``[a=rd:?:?]``

Here a is any variable which is assigned the destination register number of the first instruction.

Condition List:
----------------
This contains the evaluation statements to check the data dependencies. In case of don't care conditions, we don't check for data dependecies for that 
particular instruction. It conatins conditions for both source as well as destination registers. We can check for both consuming and non-consuming instructions.

Example of condition list: ``[?:rs1==a or rs2==a]``

Here let a be the destination register of the first instruction (assigned by assign list). Then this checks whether any of the source registers are equal to the
destination register of the previous instruction. It basically checks for read after write hazard.

Cross Coverage Queue
=====================

This is list of instruction objects in which the data is pushed in the sequence they are parsed. Whenever the queue size becomes equal to the window size, we check for all potential data hazards between the front element of the queue and the rest of the instructions according to the coverpoint and then pop the first element.

Cross Coverage Class
=====================

def __init__(self,label,coverpoint):
---------------------------------------

The cross coverage class ``cross`` is initialized with the ``label`` and ``coverpoint``. ``result`` stores the coverage for that coverpoint.

* Arguments: ``self`` instance of the class, ``label`` the instruction name, ``coverpoint`` the coverpoint to be evaluated.


.. code-block:: python

    def __init__(self,label,coverpoint):
        self.label = label
        self.coverpoint = coverpoint
        self.result = 0

An instance of a class is created for each ``(label,coverpoint)`` pair present in the CGF and all the relevant information about the coverpoint - opcode list, assign list and condition list are extracted.

def process(self, queue, window_size, addr_pairs):
----------------------------------------------------

The  ``process`` function of ``cross`` evaluates each coverpoint and updates ``result`` if there is a hit. The data in the coverpoint is evaluated against their corresponding instruction in the queue i.e. if the index of an instruction is i, then it will check and assign statments at index i of the three lists of the coverpoints. If the instruction address doesn't belong to any list of addresses in ``addr_pairs`` we treat is as a don't care. These coverpoints are checked in three steps.

 - First, the name of the first instruction is checked against the corresponding entry in the opcode list.
 - If the instruction is present, we assign its register value to a variable using ``exec`` command on the assign list elements.
 - Then we check for the conditions in the condition list using ``eval`` command.  
   The above steps are repeated until the entire coverpoint is evaluated and it's a hit or the conditions are not satisfied and the loop breaks.
   
* Arguments: ``self`` instance of the class, ``queue`` the list containing the instructions to be evaluated, ``window_size`` maximum number of instructions to be checked for any coverpoint, ``addr_pairs`` the addresses to be considered while evaluating an instruction
* Returns: None

def get_metric(self):
----------------------

It returns the coverage for that instance.

* Arguments: ``self`` instance of the class
* Returns: ``result`` the final coverage for that coverpoint

Updating the CGF
========================

 - An object dictionary ``obj_dict`` contains an instance of ``cross`` for each ``(label,coverpoint)`` pair.
 - As the instrcutions are parsed, they are appended to the ``cross_cover_queue`` which is the list of instructions to be checked.
 - When the size of queue becomes equal to the window size, for each entry in ``obj_dict``, the coverpoints are evaluated in ``process``
 - The first element of the queue is popped and the process is repeated.
 - After all the instrcutions are parsed, all the instructions in the queue are again evaluated in the above manner till there is nothing to evaluate.
 - The final metric for each ``(label,coverpoint)`` instance is updated for each node in the CGF.
 
**Examples of coverpoints**
            The window size is fixed and equal to 5.
        
            1. RAW for an add instruction followed immediately by a subtract instruction.
            
                .. code-block:: python
    
                    [(add,sub) : (add,sub) ] :: [a=rd : ? ] :: [? : rs1==a or rs2==a ]

            2. RAW on x10 register for an add instruction followed by a subtract instruction with one non-consuming/non-updating instruction in between. 
               No update happens to the rd register in between.
    
                .. code-block:: python

                    [(add,sub) : ? : (add,sub) ] :: [a=rd : ? : ? ] :: [rd==x10 : rd!=a and rs1!=a and rs2!=a : rs1==a or rs2==a ]

            3. WAW for an add instruction followed by a subtract instruction with 3 non-consuming instructions in between.

                .. code-block:: python

                    [add : ? : ? : ? : sub] :: [a=rd : ? : ? : ? : ?] :: [? : ? : ? : ? : rd==a]
                    
            4. WAW for add followed by subtract with 3 consuming instructions in between.
            
                .. code-block:: python
    
                    [(add,sub) : ? : ? : ? : (add,sub)] :: [a=rd : ? : ? : ? : ?] :: [? : rs1==a or rs2==a : rs1==a or rs2==a : rs1==a or rs2==a : rd==a]

            5. WAR for an add instruction followed immediately by a subtract instruction.
            
                .. code-block:: python
    
                    [(add,sub) : (add,sub) ] :: [a=rs1; b=rs2 : ? ] :: [? : rd==a or rd==b ]



