import discord


base_url = "https://stackuphelpcentre.zendesk.com/hc/en-us/requests/new"


start_ticket_embed = discord.Embed(
    title="Submit a request",
    description="Jumpstart on opening a ticket",
    url=base_url)


class State:


    def __init__(self, name):
        self.name = name
        self.content = ""
        self.data: dict = {}
        self.prev: State = None
        self.next: State = None
        self.branch: dict = {}


    def insert_next_state(self, state_name):
        """insert and returns this state object"""
        new_state = State(state_name)
        self.next = new_state
        new_state.prev = self
        return new_state
    

    def insert_branch_state(self, state_name):
        """insert and returns this state object"""
        new_state = State(state_name)
        self.branch[state_name] = new_state
        new_state.prev = self
        return new_state


    def update_content(self, content):
        """update this state's data, and return this state object"""
        self.content = content
        return self
    

    def update_data(self, key, value):
        self.data[key] = value
        return self
    

    def remove_data(self, key):
        self.data.popitem(key)
        return self
    

    def has_next(self):
        return self.next is not None or len(self.branch) > 0


    def has_prev(self):
        return self.prev is not None


class StateMachine:

    start_state = None
    current_state = None

    """
    States:
    ├ start
    └ issue_type
      ├ general_enquiry
      | └ open_ticket = 9094359542041
      ├ account_related
      | └ open_ticket = 10970588074137
      ├ withdrawal_related
      | ├ check_processing_days
      | └ open_ticket = 11749552676121
      ├ platform_bug
      | ├ suggest_discord
      | └ open_ticket = 11733831427737
      └ submission_related
        ├ suggest_discord
        └ open_ticket = 11733869435673
    """


    issue_type_options = {
        "General Enquiry": "general_enquiry",
        "Withdrawal-Related Matters": "withdrawal_related",
        "Submission-Related Matters": "submission_related",
        "Account-Related Matters": "account_related",
        "Platform Bug Issue": "platform_bug"
    }


    def __init__(self):
        self.current_state = self.start_state = State("start")

        branch_state = (self.current_state
                        .insert_next_state("issue_type")
                        .update_content("Choose your issue type:"))

        (branch_state
            .insert_branch_state("general_enquiry")
            .insert_next_state("open_ticket")
            .update_content("You should open a ticket.")
            .update_data("ticket-id", "9094359542041")
        )

        (branch_state
            .insert_branch_state("account_related")
            .insert_next_state("open_ticket")
            .update_content("You should open a ticket.")
            .update_data("ticket-id", "10970588074137")
        )

        (branch_state
            .insert_branch_state("withdrawal_related")
            .insert_next_state("check_processing_days")
            .update_content(
                "- Have you checked your estimated withdrawal date using `/calculate_withdrawal`?\n"
                "- Is the estimated withdrawal date earlier than today?"
            )
            .insert_next_state("open_ticket")
            .update_content("You should open a ticket.")
            .update_data("ticket-id", "11749552676121")
        )

        (branch_state
            .insert_branch_state("platform_bug")
            .insert_next_state("suggest_discord")
            .update_content(
                "You can report in #bug-error-report. "
                "Otherwise, proceed to open an official report."
            )
            .insert_next_state("open_ticket")
            .update_content("You should open a ticket.")
            .update_data("ticket-id", "11733831427737")
        )

        (branch_state
            .insert_branch_state("submission_related")
            .insert_next_state("suggest_discord")
            .update_content(
                "- Have you checked recent #re-review submission for similar issues reported?\n"
                "- Have you discussed with other stackies in #re-review submission?"
            )
            .insert_next_state("open_ticket")
            .update_content("You should open a ticket.")
            .update_data("ticket-id", "11733869435673")
        )



    def prev_state(self):
        """move to previous state"""

        assert self.current_state.prev is not None
        self.current_state = self.current_state.prev

        # Recursively go back prev state (if exist) if current_state has no content
        if self.current_state.has_prev() and self.current_state.content == "":
            self.prev_state()

    def next_state(self, branch = None):
        """move to next state"""

        next_state = self.current_state.branch[branch] if branch else self.current_state.next

        if next_state:
            self.current_state = next_state

            # Recursively skip to next state (if exists) if current_state has no content
            if self.current_state.next and self.current_state.content == "":
                self.next_state()


class TicketHelper(discord.ui.View):

    state_machine: StateMachine = None
    embed = None
    content = ""

    def load_state_ui(self):
        state = self.state_machine.current_state

        self.content = state.content
        self.embed = start_ticket_embed if state.name == "start" else None
        self.clear_items()

        if state.name == "issue_type":
            print('create')
            self.branch_select = discord.ui.Select(placeholder="Issue Type", options=
                    list(map(lambda x: discord.SelectOption(label=x), StateMachine.issue_type_options)))
            self.branch_select.callback = self.branch_next_state
            self.add_item(self.branch_select)
            self.next_btn.disabled = True
        else:
            self.branch_select = None
        
        if state.has_prev():
            self.add_item(self.back_btn)
        if state.has_next() and state.name != "issue_type":
            self.add_item(self.next_btn)

        if state.name == "open_ticket":
            ticket_form_id = state.data["ticket-id"]
            self.link_btn.url = f"{base_url}?ticket_form_id={ticket_form_id}" if ticket_form_id else base_url
            self.add_item(self.link_btn)

        ############################## TESTING ##############################
        #self.add_item(self.check_btn)
        ############################## TESTING ##############################


    def __init__(self):
        super().__init__()

        self.state_machine = StateMachine()

        self.back_btn = discord.ui.Button(label="Back", style=discord.ButtonStyle.grey, row=4)
        self.back_btn.callback = self.go_prev_state

        self.next_btn = discord.ui.Button(label="Proceed",style=discord.ButtonStyle.blurple, row=4)
        self.next_btn.callback = self.go_next_state

        self.link_btn = discord.ui.Button(label="Open Ticket",style=discord.ButtonStyle.link, row=4, url=base_url)

        ############################## TESTING ##############################
        # async def check_curr_state(interaction: discord.Interaction):
        #    await interaction.response.edit_message(content=self.state_machine.current_state.name)
            
        # self.check_btn = discord.ui.Button(label="Check",style=discord.ButtonStyle.danger)
        # self.check_btn.callback = check_curr_state


        self.state_machine.next_state()
        ############################## TESTING ##############################

        self.load_state_ui()


    async def go_prev_state(self, interaction: discord.Interaction):
        self.state_machine.prev_state()
        self.load_state_ui()

        await interaction.response.edit_message(
            content=self.content,
            embed=self.embed,
            view=self)


    async def go_next_state(self, interaction: discord.Interaction):
        self.state_machine.next_state()
        self.load_state_ui()

        await interaction.response.edit_message(
            content=self.content,
            embed=self.embed,
            view=self)
    

    async def branch_next_state(self, interaction: discord.Interaction):
        selected_issue_type = self.branch_select.values[0]
        select_branch_state = StateMachine.issue_type_options[selected_issue_type]
        
        print(select_branch_state)
        
        #"""

        self.state_machine.next_state(select_branch_state)
        self.load_state_ui()

        await interaction.response.edit_message(
            content=self.content,
            embed=self.embed,
            view=self)

        """#
        # FIXME: preferbly, selection option does not go next state immedtately,
        #        but it enables the proceed button instead

        self.next_btn.disabled = False
        
        await interaction.response.defer()

        #"""


        
