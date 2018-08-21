/* YourDuino.com Example Software Sketch
   Small Stepper Motor and Driver V1.5 06/21/17
   http://www.yourduino.com/sunshop/index.php?l=product_detail&p=126
   Shows 4-step sequence, Then 1/2 turn and back different speeds
   terry@yourduino.com */

/*-----( Import needed libraries )-----*/
#include <Stepper.h>

/*-----( Declare Constants, Pin Numbers )-----*/
//---( Number of steps per revolution of INTERNAL motor in 4-step mode )---
#define STEPS_PER_MOTOR_REVOLUTION 32   

//---( Steps per OUTPUT SHAFT of gear reduction )---
#define STEPS_PER_OUTPUT_REVOLUTION 32 * 64  //2048  

/*-----( Declare objects )-----*/
// create an instance of the stepper class, specifying
// the number of steps of the motor and the pins it's
// attached to

//The pin connections need to be pins 8,9,10,11 connected
// to Motor Driver In1, In2, In3, In4 

// Then the pins are entered here in the sequence 1-3-2-4 for proper sequencing
Stepper stepper(STEPS_PER_MOTOR_REVOLUTION, 8, 10, 9, 11);


/*-----( Declare Variables )-----*/
int Stride = 1;

// sending numbers via serial
// example 4 from http://forum.arduino.cc/index.php?topic=396450
const byte numChars = 32;
char receivedChars[numChars];   // an array to store the received data
boolean newData = false;
int dataNumber = 0;             // new for this version
int count = 0;

void setup()   /*----( SETUP: RUNS ONCE )---600rpm-*/
{
    Serial.begin(115200);
    stepper.setSpeed(600);
    count = 0;
}/*--(end setup )---*/

void loop()   /*----( LOOP: RUNS CONSTANTLY )----*/
{ 
    recvWithEndMarker();
    showNewNumberAndMove();


    /*  if sending strings
    char firstChar = receivedChars.charAt(0);
    if (isDigit(receivedChars) || firstChar == '-'){
        stepper.step(Stride * receivedChars.toInt());
    } 
    */ 
}

void recvWithEndMarker() {
    static byte ndx = 0;
    char endMarker = '>';
    char rc;
    
    if (Serial.available() > 0) {
        rc = Serial.read();

        if (rc != endMarker) {
            receivedChars[ndx] = rc;
            ndx++;
            if (ndx >= numChars) {
                ndx = numChars - 1;
            }
        }
        else {
            receivedChars[ndx] = '\0'; // terminate the string
            ndx = 0;
            newData = true;
        }
    }
}

void showNewNumberAndMove() {
    if (newData == true) {
        dataNumber = 0;             // new for this version
        dataNumber = atoi(receivedChars);   // new for this version
        /*
        Serial.print("This just in ... ");
        Serial.println(receivedChars);
        Serial.print("Data as Number ... ");    // new for this version
        Serial.println(dataNumber);     // new for this version
        */
        // move certain steps
        if (dataNumber != 987) {
            steps = Stride * dataNumber
            stepper.step(steps);
            count += steps;
        }
        else {
            Serial.println(count)
        }
        newData = false;
    }
}

/* ( THE END ) */


