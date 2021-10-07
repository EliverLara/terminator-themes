import execa from 'execa'
import minimist from 'minimist'
import createThemesJsonFile from './themes-json.mjs'
import { createNewThemesImgs, createMd } from './themes-extras.mjs'

const args = minimist(process.argv.slice(2));

const main = async() => {
    try {

        let newThemes;

        if(args.f) {
            switch(args.f){
                case "all":
                    newThemes = await execa.stdout('ls', [ '../schemes']);
                    newThemes = newThemes.split('\n');
                    break;
                case "new":
                    newThemes = await execa.stdout('git', [ '-C', '../schemes', 'ls-files', '--others', '--exclude-standard']);
                    newThemes = newThemes.split('\n');
                    break;
                default:
                    newThemes = args._ ? [...args._, args.f]: [args.f];
                    break;
            }
        } else { throw new Error("f argument is required"); }

        await createThemesJsonFile()
        await createNewThemesImgs(newThemes);
        await createMd();

    }catch(err) {
        console.log(err)
    }
} 

main()