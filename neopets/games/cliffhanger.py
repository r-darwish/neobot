import logging
import re
from neopets.common import PageParseError, get_np


class UnknownAnswerError(Exception):
    def __init__(self, pattern):
        super(UnknownAnswerError, self).__init__(
            'Unknown answer for pattern %s' % (pattern, ))
        self.pattern = pattern


class MultipleAnswersError(Exception):
    def __init__(self, possible_answers):
        super(MultipleAnswersError, self).__init__(
            'Multiple answers %s' % (possible_answers, ))
        self.possible_answers = possible_answers


class Cliffhanger(object):
    _CELL_ATTERS = dict(bgcolor='skyblue')
    _ANSWERS = [
        'Happy gadgadsbogen day',
        'No news is impossible',
        'Super Glue is forever',
        'Better late than never',
        'Meercas despise red neggs',
        'Scorchios like hot places',
        'Dr Frank Sloth is green',
        'All roads lead to neopia',
        'Koi invented the robotic fish',
        'Dung furniture stinks like dung',
        'Keep your broken toys clean',
        'Today is your lucky day',
        'Nimmos are very spiritual beings',
        'A buzz will never sting you',
        'Be nice to Shoyrus or else',
        'Mr black makes the best shopkeeper',
        'The beader has a beaming smile',
        'The techo is a tree acrobat',
        'Chia bombers are mud slinging fools',
        'Only real card sharks play cheat',
        'Garon loves an endless challenging maze',
        'Great neopets are not always wise',
        'Moogi is a true poogle racer',
        'Fuzios wear the coolest red shoes',
        'Number six is on the run',
        'Carrots are so expensive these days',
        'Faeries are quite fond of reading',
        'Korbats are creatures of the night',
        'Skeiths are strong but very lazy',
        'Chombies are shy and eat plants',
        'Flotsams are no longer limited edition',
        'Kacheekers is a two player game',
        'Tyrannians will eat everything and anything',
        'An air of mystery surrounds the acara',
        'The Cybunny is the fastest neopet ever',
        'The pen is mightier than the pencil',
        'The Snowager sleeps most of its life',
        'You cannot teach an old grarrl mathematics',
        'Most Wild Kikos Swim in Kiko Lake',
        'Some neggs will bring you big disappointment',
        'Some neggs will bring you big neopoints',
        'Unis just love looking at their reflection',
        'When there is smoke there is pollution',
        'Kyrii take special pride in their fur',
        'Maybe the missing link is really missing',
        'Never underestimate the power of streaky bacon',
        'Faerie food is food from the heavens',
        'Frolic in the snow of happy valley',
        'Mister pickles has a terrible tigersquash habit',
        'Jubjubs defend themselves with their deafening screech',
        'Kauvara mixes up potions like no other',
        'Neopian inflation is a fact of life',
        'Poogles look the best in frozen collars',
        'Tornado rings and cement mixers are unstoppable',
        'Uggaroo gets tricky with his coconut shells',
        'Chombies hate fungus balls with a passion',
        'Asparagus is the food of the gods',
        'A miss is as good as a mister',
        'A neopoint saved is a neopoint not enough',
        'A tuskaninny named colin lives on terror mountain',
        'An iron rod bends while it is hot',
        'Do not bathe if there is no water',
        'Dr Death is the keeper of disowned neopets',
        'If your hedge needs trimming call a chomby',
        'Pet rocks make the most playful of petpets',
        'The advent calendar is only open in december',
        'The Alien Aisha Vending Machine serves great good',
        'The big spender is an international jet setter',
        'The Bruce is from Snowy Valley High School',
        'The healing springs mends your wounds after battle',
        'The hidden tower is for big spenders only',
        'The library faerie tends to the crossword puzzle',
        'The tatsu population was almost reduced to extinction',
        'You should try to raise your hit points',
        'Have you trained your pet for the Battledome',
        'Keep your pet company with a neopet pet',
        'Flame the Tame is a ferocious feline fireball',
        'Whack a beast and win some major points',
        'Doctor Sloth tried to mutate neopets but failed',
        'Faerie pancakes go great with crazy crisp tacos',
        'Kougras are said to bring very good luck',
        'Scratch my back and I will scratch yours',
        'Children should not be seen spanked or grounded',
        'Kacheeks have mastered the art of picking flowers',
        'Kikoughela is a fancy word for cough medicine',
        'Snowbeasts love to attack grundos with mud snowballs',
        'An idle mind is the best way to relax',
        'Do not open a shop if you cannot smile',
        'Do not try to talk to a shy peophin',
        'It is always better to give than to receive',
        'Get three times the taste with the triple dog',
        'Let every zafara take care of its own tail',
        'Put all of your neopoints on poogle number two',
        'The barking of Lupes does not hurt the clouds',
        'The battledome is near but the way is icy',
        'The meat of a sporkle is bitter and inedible',
        'The quick brown fox jumps over the lazy dog',
        'The tyrannian volcano is the hottest place in neopia',
        'Look out for the moehog transmogrification potion lurking around',
        'Mika and Carassa Want You To Buy Their Junk',
        'Take your pet to tyrammet for a fabulous time',
        'Your pet deserves a nice stay at the neolodge',
        'Enter the lair of the beast if you dare',
        'Every neopet should have a job and a corndog',
        'Stego is a baby stegosaurus that all neopets love',
        'Treat your usul well and it will be useful',
        'Plesio is the captain of the tyrannian sea division',
        'Poogle five is very chubby but is lightning quick',
        'Sticks n stones are like the greatest band ever',
        'Terror Mountain is home to the infamous Ski Lodge',
        'Magical ice weapons are from the ice cave walls',
        'Meercas are to blame for all the stolen fuzzles',
        'Neopets battledome is not for the weak or sensitive',
        'Poogles have extremely sharp teeth and they are cuddly',
        'Uggaroo follows footsteps to find food for his family',
        'Congratulations to everybody who helped defeat the evil monoceraptor',
        'A chia who is a mocker dances without a tamborine',
        'If you live with lupes you will learn to howl',
        'Oh where is the tooth faerie when you need her',
        'To know and to act are one and the same',
        'All neopets can find a job at the employment agency',
        'The best thing to spend on your neopet is time',
        'The kindhearted faerie queen rules faerieland with a big smile',
        'The lair of the beast is cold and dark inside',
        'The meerca is super fast making it difficult to catch',
        'The pound is not the place to keep streaky bacon',
        'The sunken city of Maraqua has some great hidden treasures',
        'The tyrannian jungle is full of thick muddle and mash',
        'The wise aisha has long ears and a short tongue',
        'Yes boy ice cream sell out all of their shows',
        'Love your neopet but do not hug it too much',
        'Only ask of the Queen Faerie what you really need',
        'Some neohomes are made with mud and dung and straw',
        'With the right training Tuskaninnies can become quite fearsome fighters',
        'Chias are loveable little characters who are full of joy',
        'Store all of your Neopian trading cards in your neodeck',
        'There is nothing like a tall glass of slime potion',
        'Under a tattered cloak you will generally find doctor sloth',
        'Become a BattleDome master by training on the Mystery Island',
        'Better to be safe than meet up with a monocerous',
        'Grarrg is the tyrannian battle master that takes no slack',
        'Please wipe your feet before you enter the Scorchio den',
        'Faeries bend down their wings to a seeker of knowledge',
        'Kyruggi is the grand elder in the tyrannian town hall',
        'Meercas are talented pranksters that take pride in their tails',
        'Bouncing around on its tail the blumaroo is quite happy',
        'A journey of a million miles begins on the marketplace map',
        'Be sure to visit the Neggery for some great magical neggs',
        'By all means trust in neopia but tie your camel first',
        'Do not wake the snowager unless you want to be eaten',
        'If a pteri and lenny were to race neither would win',
        'Ask a lot of questions but only take what is offered',
        'The bluna was first sighted under the ice caps of tyrannia',
        'The Neopedia is a good place to start your Neopian Adventures',
        'You cannot wake a Bruce who is pretending to be asleep',
        'You know the soup kitchen is a great place to go',
        'You know you can create a free homepage for your pet',
        'You probably do not want to know what that odor is',
        'Give the wheel of excitement a spin or two or three',
        'Have you told your friends about the greatest site on earth',
        'Kaus love to sing although they only know a single note',
        'Make certain your pet is well equipped before entering the battledome',
        'Only mad gelerts and englishmen go out in the noonday sun',
        'When eating a radioactive negg remember the pet who planted it',
        'When friends ask about the battledome say there is no tomorrow',
        'When the blind lead the blind get out of the way',
        'Bruce could talk under wet cement with a mouthful of marbles',
        'Count Von Roo is one of the nastier denizens of neopia',
        'Every buzz is a kau in the eyes of its mother',
        'Space slushies are just the thing on a cold winter day',
        'Faerie poachers hang out in faerieland with their jars wide open',
        'Listen to your pet or your tongue will keep you deaf',
        'Poogle number five always wins unless he trips over a hurdle',
        'Grarrls are ferocious creatures or at least they try to be',
        'Jetsams are the meanest Neopets to ever swim the Neopian sea',
        'Tyrannia is the prehistoric kingdom miles beneath the surface of neopia',
        'A kyrii will get very upset if its hair gets messed up',
        'By all means make neofriends with peophins but learn to swim first',
        'Do not be in a hurry to tie what you cannot untie',
        'Do not speak of an elephante if there is no tree nearby',
        'Do not think there are no jetsams if the water is calm',
        'If you see a man riding a wooden stick ask him why',
        'If you want to have lots of adventures then adopt a wocky',
        'Eat all day at the giant omelette but do not be greedy',
        'Fly around the canyons of tyrannia shooting the evil pterodactyls and grarrls',
        'The Grarrl will roar and ten eggs will hatch into baby grarrls',
        'The Snow Faerie Quest is for those that can brave the cold',
        'The wheel of mediocrity is officially the most second rate game around',
        'You should not throw baseballs up when the ceiling fan is on',
        'When an Elephante is in trouble even a Nimmo will kick him',
        'Catch the halter rope and it will lead you to the kau',
        'Dirty snow is the best way to make your battledome opponent mad',
        'Krawk have been known to be as strong as full grown neopets',
        'There is only one ryshu and there is only one techo master',
        'Uggsul invites you to play a game or two of tyranu evavu',
        'Myncies love to hug their plushies and eat sap on a stick',
        'Everyone loves to drink a hot cup of borovan now and then',
        'Jarbjarb likes to watch the tyrannian sunset while eating a ransaurus steak',
        'Quiggles spend all day splashing around in the pool at the neolodge',
        'Experience is the comb that nature gives us when we are bald',
        'Cliffhanger is a brilliant game that will make your pet more intelligent',
        'A Scorchio is a good storyteller if it can make a Skeith listen',
        'Do not be greedy and buy every single food item from the shops',
        'If at first you do not succeed play the ice caves puzzle again',
        'If you go too slow try to keep your worms in a tin',
        'If your totem is made of wax do not walk in the sun',
        'It makes total sense to have a dung carpet in your dung neohome',
        'We never know the worth of items till the wishing well is dry',
        'The Neopian Hospital will help get your pet on the road to recovery',
        'You can lead a kau to water but you cannot make it drink',
        'Bang and smash your way to the top in the bumper cars game',
        'Myncies come from large families and eat their dinner up in the trees',
        'Faerieland is not for pets that are afraid of heights or fluffy clouds',
        'Why beg for stuff when you can make money at the wheel of excitement',
        'You know you should never talk to Bruce even when his mouth is full',
        'Your neopet will need a mint after eating a chili cheese dog with onions',
        'Building a neohome is a way to build a foundation for your little pets',
        'The beast that lives in the tyrannian mountains welcomes all visitors with a sharp smile',
        'The whisper of an acara can be heard farther than the roar of a wocky',
        'You really have to be well trained if you want to own a wild reptillior',
        'Bronto bites are all the rage and they are meaty and very easy to carry',
    ]

    def __init__(self, account):
        self._account = account
        self._np_earned = 0
        self._round = 1
        self._before = None

    def __str__(self):
        return 'Cliffhanger'

    def run(self):
        d = self._account.get('games/cliffhanger/cliffhanger.phtml')
        d.addCallback(self._on_start_game)
        return d

    def _on_start_game(self, page):
        logging.info('Cliffhanger start!')
        return self._start_round(page)

    def _start_round(self, page):
        self._before = get_np(page)
        logging.debug('Starting round %d (NP: %d)', self._round, self._before)
        d = self._account.post('games/cliffhanger/process_cliffhanger.phtml',
                               dict(start_game='true', game_skill='3'))
        d.addCallback(self._solve)
        return d

    def _solve(self, page):
        puzzle = page.find(text='YOUR PUZZLE')
        if not puzzle:
            raise PageParseError(page)

        table = puzzle.findParent('table')
        cell = table.find('td', attrs=self._CELL_ATTERS)
        regex = '^'
        for elem in cell.contents[1:-3]:
            if not hasattr(elem, 'name'):
                regex += ' '
            elif elem.name == 'b':
                regex += '\w'
            elif elem.name == 'br':
                regex += ' '
        regex += '$'
        regex = re.compile(regex)
        possible_answers = [a for a in self._ANSWERS if regex.search(a)]

        if not possible_answers:
            raise UnknownAnswerError(cell.text)
        if len(possible_answers) > 1:
            raise MultipleAnswersError(possible_answers)

        answer = possible_answers[0]
        logging.debug('Answer is \'%s\'', answer)

        d = self._account.post('games/cliffhanger/process_cliffhanger.phtml',
                               dict(solve_puzzle=answer))
        d.addCallback(self._solved)
        return d

    def _solved(self, page):
        if page.find(text='You win!!!'):
            logging.info("Won!")
        else:
            logging.info("Lost!")

        np = get_np(page)
        if np != self._before:
            self._round += 1
            logging.info('Going for another round')
            return self._start_round(page)
        else:
            logging.info('Done for today')
